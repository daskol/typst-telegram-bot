from json import dumps
from pathlib import Path
from typing import Any

from aiohttp import web
from aiohttp.web import (HTTPBadRequest, HTTPRequestEntityTooLarge, Request,
                         Response)

from typst_telegram.render import EXPR_MAX_SIZE, Context, RenderingError


async def get_ping(request):
    return Response(text='Pong.\n')


async def get_render(request: Request):
    expr = request.query.get('expr')
    if len(expr) > EXPR_MAX_SIZE:
        raise HTTPRequestEntityTooLarge(EXPR_MAX_SIZE, len(expr))

    config: dict[str, Any] = request.app.config
    context = Context(root_dir=config['root_dir'])

    try:
        img = await context.render(expr)
    except RenderingError as e:
        json = dumps(e.to_dict(), ensure_ascii=False)
        raise HTTPBadRequest(body=json, content_type='application/json') from e
    return Response(body=img)


app = web.Application()
app.add_routes([web.get('/ping', get_ping), web.get('/render', get_render)])


def serve(host, port, root_dir: Path = Path('.'), **kwargs):
    app.config = {'root_dir': root_dir}
    web.run_app(app, host=host, port=port)
