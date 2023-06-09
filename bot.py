#!/usr/bin/env python

import logging
from hashlib import md5
from os import getenv

from aiogram import Bot, Dispatcher, executor, types
from aiohttp.client import ClientError, ClientSession

TELEGRAM_BOT_API_TOKEN = getenv('TELEGRAM_BOT_API_TOKEN')


GREATINGS = (r'Hi\! I\'m @TypstBot\! I render math expressions written in '
             r'[typst](https://typst.app) markup languge to images\.')

FAILURE = (r'Rendering error\. First\, check '
           r'[correctness](https://typst.app/docs/reference/math/) of the '
           r'expression\; otherwise\, try again later\.')

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_API_TOKEN)
router = Dispatcher(bot)


async def on_startup(router: Dispatcher):
    router.sess = ClientSession('http://localhost:8080')


@router.message_handler(commands=['start', 'help'])
async def welcome(message: types.Message):
    await message.answer(GREATINGS,
                         parse_mode='MarkdownV2',
                         disable_web_page_preview=True)


@router.message_handler()
async def render(message: types.Message):
    if not message.text:
        await message.answer('Only text messages are expected.')
        return

    try:
        sess: ClientSession = router.sess
        async with sess.get('/render', params={'expr': message.text}) as res:
            img = await res.read()
        await message.answer_photo(img)
    except ClientError:
        await message.answer(FAILURE,
                             parse_mode='MarkdownV2',
                             disable_web_page_preview=True)
        raise


@router.inline_handler()
async def render_inline(message: types.InlineQuery):
    text = message.query or 'F(x) = integral f(x) d x + C'
    input_content = types.InputTextMessageContent(text)
    result_id: str = md5(text.encode()).hexdigest()
    item = types.InlineQueryResultArticle(
        id=result_id,
        title=text,
        input_message_content=input_content,
    )
    await bot.answer_inline_query(message.id, results=[item])


if __name__ == '__main__':
    executor.start_polling(router, skip_updates=True, on_startup=on_startup)
