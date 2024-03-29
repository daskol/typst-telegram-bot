import logging
from asyncio import sleep
from collections import defaultdict
from csv import DictReader, DictWriter
from dataclasses import asdict, dataclass
from enum import Enum
from json import dumps
from os import getenv
from pathlib import Path
from typing import IO, Any, Mapping, Optional, Self

from aiogram import Bot


class Status(Enum):

    UNKNOWN = 'unknown'

    FAILED = 'failed'

    SENT = 'sent'

    SKIPPED = 'skipped'


@dataclass
class Recipient:

    uid: int

    status: str = 'unknown'

    def __post_init__(self):
        if self.status not in ('unknown', 'failed', 'sent', 'skipped'):
            self.status = 'unknown'


def read_mailing_list(path: Path):
    with open(path) as fin:
        reader = DictReader(fin)
        recipients = []
        for row in reader:
            entry = Recipient(uid=int(row['uid']), status=row.get('status'))
            recipients.append(entry)
    return recipients


class MailingList:

    def __init__(self, recipients: list[Recipient],
                 fp_output: Optional[IO] = None):
        self.recipients = recipients
        self.fp_output = fp_output
        self.offset = 0
        self.writer: Optional[DictWriter] = None
        self.stats = defaultdict(int)

    def __del__(self):
        self.close()

    def __len__(self):
        return len(self.recipients)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(length={len(self.recipients)})'

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> Recipient:
        if self.offset >= len(self.recipients):
            raise StopIteration
        recipient = self.recipients[self.offset]
        self.offset += 1
        return recipient

    def close(self):
        if self.writer is not None:
            self.writer = None
        if self.fp_output is not None:
            self.fp_output.flush()
            self.fp_output.close()
            self.fp_output = None

    @classmethod
    def from_paths(cls, input_: Path, output: Optional[Path]):
        recipients = read_mailing_list(input_)
        fp_output = None
        if output is not None:
            fp_output = open(output, 'a')  # Append mode.
        return cls(recipients, fp_output)

    def report(self, recipient: Recipient, status: Optional[str] = None):
        # Update status statistics.
        row = asdict(recipient)
        if status is not None:
            row['status'] = status
        self.stats[row['status']] += 1

        # If there is no output file for logging statuses then just exit.
        if self.fp_output is None:
            return self
        # If there is not CSV-writer, then create it and write header.
        if self.writer is None:
            self.writer = DictWriter(self.fp_output, ['uid', 'status'])
            self.writer.writeheader()
        # If there is explicit status then uses recipient status.
        self.writer.writerow(row)


async def _announce(bot: Bot, ml: MailingList, msg: Mapping[str, Any],
                    dry_run: bool = False):
    disable_web_page_preview = msg.get('disable_web_page_preview')
    for recipient in ml:
        if (status := recipient.status) == 'sent':
            status = 'skipped'
        elif not dry_run:
            try:
                await bot.send_message(
                    chat_id=recipient.uid,
                    text=msg['text'],
                    parse_mode='MarkdownV2',
                    reply_markup=msg.get('reply_markup'),
                    disable_web_page_preview=disable_web_page_preview,
                    disable_notification=msg.get('disable_notification'),
                )
            except Exception:
                status = 'failed'
            else:
                status = 'sent'
        ml.report(recipient, status)


async def announce(mailing_list: MailingList, message: Mapping[str, Any],
                   dry_run: bool = False):
    bot_token = getenv('TELEGRAM_BOT_API_TOKEN')
    bot = Bot(token=bot_token)
    pos = bot_token.find(':')
    pos = max(pos, 8)
    logging.info('use bot token %s:***', bot_token[:pos])

    info = dict(await bot.get_me())
    logging.info('bot info is %s', dumps(info, ensure_ascii=False, indent=2))
    logging.info('send message %s to %d recipients',
                 dumps(message, ensure_ascii=False, indent=2),
                 len(mailing_list))

    if dry_run:
        logging.info('broadcast messages in dry run mode')
    else:
        for timeout in range(3, 0, -1):
            logging.info('wait %s seconds before sending starts', timeout)
            await sleep(1)
        logging.info('start sending notifications')

    try:
        await _announce(bot, mailing_list, message, dry_run)
    finally:
        await (await bot.get_session()).close()

    logging.info('sending statistics: %s', dumps(mailing_list.stats))
