from asyncio import run
from sys import stdout

from aiohttp.client import ClientSession


async def render(sess: ClientSession, expr: str):
    params = {'expr': expr}
    async with sess.get('/render', params=params) as res:
        return await res.read()


async def main(expr: str):
    async with ClientSession('http://localhost:8080') as sess:
        img = await render(sess, expr)
        stdout.buffer.write(img)
        stdout.flush()


if __name__ == '__main__':
    run(main('y = x^2'))
