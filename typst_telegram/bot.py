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

RENDERING_ERROR = ('Rendering error\\(s\\)\\.\n'
                   '```errors\n'
                   '{errors}\n'
                   '```')

bot = Bot(token=TELEGRAM_BOT_API_TOKEN)
router = Dispatcher(bot)


async def on_startup(router: Dispatcher):
    endpoint = router.config['endpoint']
    logging.info('create rendering service client: endpoint%s', endpoint)
    router.sess = ClientSession(endpoint)


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
            from http import HTTPStatus
            if res.status == HTTPStatus.OK:
                img = await res.read()
            elif res.status == HTTPStatus.BAD_REQUEST:
                json = await res.json()
                errors = json['errors']
                reason = '\n'.join(err['reason'] for err in errors)
                text = RENDERING_ERROR.format(errors=reason)
                await message.answer(text, parse_mode='MarkdownV2',
                                     disable_web_page_preview=True)
                return
            else:
                res.raise_for_status()
        await message.answer_photo(img)
    except ClientError:
        await message.answer(FAILURE, parse_mode='MarkdownV2',
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


def serve(endpoint: str):
    router.config = {'endpoint': endpoint}
    executor.start_polling(router, skip_updates=True, on_startup=on_startup)
