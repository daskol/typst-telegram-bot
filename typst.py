#!/usr/bin/env python

from asyncio.subprocess import PIPE, create_subprocess_exec
from dataclasses import dataclass
from pathlib import Path

from aiohttp import web
from aiohttp.web import Request, Response, HTTPRequestEntityTooLarge

EXPR_TEMPLATE = """\
#set page(width: auto, height: auto, margin: (x: 0pt, y: 0pt))
$ {expr} $
"""

EXPR_MAX_SIZE = 1024


@dataclass
class Context:

    root_dir: Path = Path('.')

    dpi: int = 300

    mimetype: str = 'image/png'

    async def render(self, expr: str):
        path_typ = self.root_dir / 'main.typ'
        path_pdf = self.root_dir / 'main.pdf'

        with open(path_typ, 'w') as fout:
            fout.write(EXPR_TEMPLATE.format(expr=expr))

        pid = await create_subprocess_exec('typst', path_typ, path_pdf)
        if (retcode := await pid.wait()) != 0:
            print('ERR typst retcode:', retcode)

        cmd = ['pdftoppm', '-r', str(self.dpi)]
        if self.mimetype == 'image/png':
            cmd.append('-png')
        cmd.append(path_pdf)
        pid = await create_subprocess_exec(*cmd, stdout=PIPE)
        img = await pid.stdout.read()
        if (retcode := await pid.wait()) != 0:
            print('ERR pdftoppm retcode:', retcode)
        return img


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

if __name__ == '__main__':
    web.run_app(app)
