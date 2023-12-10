import logging
import re
from asyncio import StreamReader
from asyncio.subprocess import PIPE, create_subprocess_exec
from codecs import getincrementaldecoder
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

EXPR_TEMPLATE = """\
#set page(width: auto, height: auto, margin: (x: 0pt, y: 0pt))
$ {expr} $
"""

EXPR_MAX_SIZE = 1024

RE_ERROR = re.compile(
    r'^(?P<filename>.*):(?P<line>\d+):(?P<column>\d+): error: (?P<reason>.*)$')


class RenderingError(RuntimeError):

    def __init__(self, stdout: str, stderr: str, errors: list[dict[str, Any]]):
        self.stdout = stdout
        self.stderr = stderr
        self.errors = errors

    def to_dict(self):
        return {'stdout': self.stdout, 'stderr': self.stderr,
                'errors': self.errors}


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
        with TemporaryDirectory(dir=self.root_dir) as tmpdir:
            return await self.render_at(expr, Path(tmpdir))

    async def render_at(self, expr: str, root_dir: Path):
        path_typ = root_dir / 'main.typ'
        path_png = root_dir / 'main.png'

        with open(path_typ, 'w') as fout:
            fout.write(EXPR_TEMPLATE.format(expr=expr))

        cmd = ('typst', 'compile', '--diagnostic-format=short', '--format=png',
               f'--ppi={self.dpi}', path_typ, path_png)
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        if (retcode := await proc.wait()) != 0:
            logging.error('typst compiler failed with retcode %d', retcode)
            decoded = partial(DecodingStreamReader, encoding='utf-8',
                              errors='backslashreplace')
            kwargs = {'stdout': await decoded(proc.stdout).read(),
                      'stderr': await decoded(proc.stderr).read(),
                      'errors': []}
            for m in RE_ERROR.finditer(kwargs['stderr']):
                error = m.groupdict()
                error['line'] = int(error['line'])
                error['column'] = int(error['column'])
                kwargs['errors'].append(error)
            raise RenderingError(**kwargs)

        with open(path_png, 'rb') as fout:
            return fout.read()
