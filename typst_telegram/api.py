import logging
import re
from asyncio import StreamReader
from functools import partial
from asyncio.subprocess import PIPE, create_subprocess_exec
from dataclasses import dataclass
from pathlib import Path
from json import dumps
from codecs import getincrementaldecoder
from aiohttp.web import HTTPBadRequest, HTTPInternalServerError

from aiohttp import web
from aiohttp.web import Request, Response, HTTPRequestEntityTooLarge

EXPR_TEMPLATE = """\
#set page(width: auto, height: auto, margin: (x: 0pt, y: 0pt))
$ {expr} $
"""

EXPR_MAX_SIZE = 1024

RE_ERROR = re.compile(
    r'^(?P<filename>.*):(?P<line>\d+):(?P<column>\d+): error: (?P<reason>.*)$')


class DecodingStreamReader:

    def __init__(self, stream: StreamReader, encoding='utf-8',
                 errors='strict'):
        self.stream = stream
        self.decoder = getincrementaldecoder(encoding)(errors=errors)

    def at_eof(self):
        return self.stream.at_eof()

    async def read(self, n=-1):
        data = await self.stream.read(n)
        if isinstance(data, (bytes, bytearray)):
            data = self.decoder.decode(data)
        return data


@dataclass
class Context:

    root_dir: Path = Path('.')

    dpi: int = 300

    mimetype: str = 'image/png'

    async def render(self, expr: str):
        path_typ = self.root_dir / 'main.typ'
        path_png = self.root_dir / 'main.png'

        with open(path_typ, 'w') as fout:
            fout.write(EXPR_TEMPLATE.format(expr=expr))

        cmd = ('typst', 'compile', '--diagnostic-format=short', '--format=png',
               f'--ppi={self.dpi}', path_typ, path_png)
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        if (retcode := await proc.wait()) != 0:
            logging.error('typst compiler failed with retcode %d', retcode)
            decoded = partial(DecodingStreamReader, encoding='utf-8',
                              errors='backslashreplace')
            body = {'stdout': await decoded(proc.stdout).read(),
                    'stderr': await decoded(proc.stderr).read(),
                    'errors': []}
            for m in RE_ERROR.finditer(body['stderr']):
                error = m.groupdict()
                error['line'] = int(error['line'])
                error['column'] = int(error['column'])
                body['errors'].append(error)
            json = dumps(body, ensure_ascii=False)
            raise HTTPBadRequest(body=json, content_type='application/json')

        with open(path_png, 'rb') as fout:
            return fout.read()


async def get_ping(request):
    return Response(text='Pong.\n')


async def get_render(request: Request):
    expr = request.query.get('expr')
    if len(expr) > EXPR_MAX_SIZE:
        raise HTTPRequestEntityTooLarge(EXPR_MAX_SIZE, len(expr))
    img = await Context().render(expr)
    return Response(body=img)


app = web.Application()
app.add_routes([web.get('/ping', get_ping), web.get('/render', get_render)])


def serve(host, port, **kwargs):
    web.run_app(app, host=host, port=port)
