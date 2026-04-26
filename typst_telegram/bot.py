import logging
from hashlib import md5
from http import HTTPStatus
from os import getenv

from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, LinkPreviewOptions
from aiohttp.client import ClientError, ClientSession

from typst_telegram.stats import UserStats

TELEGRAM_BOT_API_TOKEN = getenv('TELEGRAM_BOT_API_TOKEN')

TELEGRAM_MAX_ASPECT_RATIO = 20

TELEGRAM_MAX_EDGE_SIZE = 10_000  # width + height

TELEGRAM_MAX_IMAGE_SIZE = 10485760  # 10Mb


GREATINGS = (r'Hi\! I\'m @TypstBot\! I render math expressions written in '
             r'[typst](https://typst.app) markup languge to images\.')

FAILURE = (r'Rendering error\. First\, check '
           r'[correctness](https://typst.app/docs/reference/math/) of the '
           r'expression\; otherwise\, try again later\.')

RENDERING_ERROR = ('Rendering error\\(s\\)\\.\n'
                   '```errors\n'
                   '{errors}\n'
                   '```')

IMAGE_TOO_LARGE_ERROR = (
    r'⚠️ Resulting image exceeds Telegram\'s limit at 10Mb (see [Telegram Bot '
    r'API](https://core.telegram.org/bots/api#sendphoto))\.')

IMAGE_BAD_SHAPE_ERROR = (
    '⚠️ Resulting image exceeds Telegram\'s limit: '
    '\\(a\\) aspect ratio ≤ 20 and '
    '\\(b\\) width/height ≤ 10k pixels \\(see [Telegram Bot API]'
    '(https://core.telegram.org/bots/api#sendphoto)\\)\\.\n'
    '\n'
    'Try to wrap your equation on new line with backslash \\(\\\\\\)\\.')

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

bot = Bot(token=TELEGRAM_BOT_API_TOKEN)
router = Dispatcher()


@router.message(Command('start', 'help'))
async def welcome(message: types.Message):
    await message.answer(GREATINGS,
                         parse_mode='MarkdownV2',
                         link_preview_options=NO_PREVIEW)


@router.message()
async def render(message: types.Message, sess: ClientSession,
                 stats: UserStats | None = None):
    if stats is not None and message.from_user is not None:
        stats.record(message.from_user.id, message.from_user.username,
                     message.from_user.first_name)

    if not message.text:
        await message.answer('Only text messages are expected.')
        return

    try:
        async with sess.get('/render', params={'expr': message.text}) as res:
            if res.status == HTTPStatus.OK:
                img = await res.read()
            elif res.status == HTTPStatus.BAD_REQUEST:
                json = await res.json()
                errors = json['errors']
                reason = '\n'.join(err['reason'] for err in errors)
                text = RENDERING_ERROR.format(errors=reason)
                await message.answer(text, parse_mode='MarkdownV2',
                                     link_preview_options=NO_PREVIEW)
                return
            else:
                res.raise_for_status()
    except ClientError:
        await message.answer(FAILURE, parse_mode='MarkdownV2',
                             link_preview_options=NO_PREVIEW)
        raise

    # At this point we assume that we have a valid image ready to send back to
    # user. The final issue is to check image limits.
    if len(img) > TELEGRAM_MAX_IMAGE_SIZE:
        await message.answer(IMAGE_TOO_LARGE_ERROR, parse_mode='MarkdownV2',
                             link_preview_options=NO_PREVIEW)
    else:
        try:
            await message.answer_photo(BufferedInputFile(img, 'render.png'))
        except TelegramBadRequest:
            await message.answer(
                IMAGE_BAD_SHAPE_ERROR, parse_mode='MarkdownV2',
                link_preview_options=NO_PREVIEW)


@router.callback_query()
async def handle_callback_query(query: types.CallbackQuery):
    logging.info('handle callback query: data=%s', query.data)
    await query.message.edit_reply_markup(reply_markup=None)


@router.inline_query()
async def render_inline(message: types.InlineQuery,
                        stats: UserStats | None = None):
    if stats is not None and message.from_user is not None:
        stats.record(message.from_user.id, message.from_user.username,
                     message.from_user.first_name)
    text = message.query or 'F(x) = integral f(x) d x + C'
    input_content = types.InputTextMessageContent(message_text=text)
    result_id: str = md5(text.encode()).hexdigest()
    item = types.InlineQueryResultArticle(
        id=result_id,
        title=text,
        input_message_content=input_content,
    )
    await message.answer(results=[item])


async def serve(endpoint: str, stats: UserStats | None = None):
    async with ClientSession(endpoint) as sess:
        await router.start_polling(bot, skip_updates=True, sess=sess,
                                   stats=stats)
