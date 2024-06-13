import logging
import re
import sys
from argparse import (ArgumentParser, ArgumentTypeError, BooleanOptionalAction,
                      FileType, Namespace)
from asyncio import run
from inspect import iscoroutinefunction
from json import load
from pathlib import Path
from sys import stderr

try:
    from typst_telegram.version import __version__
except ImportError:
    __version__ = None

LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warn': logging.WARN,
    'error': logging.ERROR,
}


class PathType:

    def __init__(self, exists=False, not_dir=False, not_file=False):
        self.exists = exists
        self.check_dir = not_dir
        self.check_file = not_file

    def __call__(self, value: str) -> Path:
        path = Path(value)

        # If there is no check for path existance then exit.
        if not self.exists:
            return path

        # Check that path exists.
        if not path.exists():
            raise ArgumentTypeError(f'path does not exist: {path}')

        # Check type of a filesystem object referenced by path.
        if self.check_dir and path.is_dir():
            raise ArgumentTypeError(f'directory is not allowed: {path}')

        if self.check_file and path.is_file():
            raise ArgumentTypeError(f'file is not allowed: {path}')

        return path


class LengthType:

    ABSOLUTES = ('pt', 'mm', 'cm', 'in')

    RELATIVES = ('em',)

    SUFFIX = re.compile(r'(.*)(' + '|'.join(ABSOLUTES + RELATIVES) + r')')

    def __call__(self, value: str) -> str:
        if (m := LengthType.SUFFIX.match(value)) is None:
            raise ArgumentTypeError(f'unknown length unit: {value}')
        try:
            prefix: str = m.group(1)
            float(prefix)
        except ValueError:
            raise ArgumentTypeError(f'unknown length unit: {value}')
        return value


async def announce(ns: Namespace):
    from typst_telegram.crm import MailingList, announce
    ml = MailingList.from_paths(ns.recipients, ns.output)
    with open(ns.message) as fin:
        msg = load(fin)
    await announce(ml, msg, dry_run=ns.dry_run)


def help_(args: Namespace):
    parser.print_help()


def render(ns: Namespace):
    raise NotImplementedError


def serve(ns: Namespace):
    raise RuntimeError('Unreachable execution branch.')


def serve_api(ns: Namespace):
    if ns.endpoint is None:
        ns.endpoint = f'http://{ns.interface}:{ns.port}'
        logging.info('no endpoint specified: infer it from arguments: %s',
                     ns.endpoint)

    root_dir: Path = ns.root_dir
    root_dir.mkdir(exist_ok=True, parents=True)
    logging.info('use directory %s as a scratchpad for compilation', root_dir)

    kwargs = vars(ns)
    kwargs.pop('root_dir')

    render_config = {}
    for key in ('ppi', 'margin'):
        render_config[key] = kwargs[f'render_{key}']

    from typst_telegram.api import serve
    return serve(host=kwargs.pop('interface'), port=kwargs.pop('port'),
                 root_dir=root_dir, render_config=render_config, **kwargs)


def serve_bot(ns: Namespace):
    from typst_telegram.bot import serve
    serve(ns.endpoint)


def version(ns: Namespace):
    print('version', __version__)


def main():
    args: Namespace = parser.parse_args()
    # Parse command line arguments. If no subcommand were run then show usage
    # and exit. We assume that only main parser (super command) has valid value
    # in func attribute.
    args = parser.parse_args()
    if args.func is None:
        parser.print_usage()
        return

    # Set up basic logging configuration.
    if (stream := args.log_output) is None:
        stream = stderr

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        level=LOG_LEVELS[args.log_level],
                        stream=stream)

    # Dispatch CLI subcommand to corresponding handler.
    if iscoroutinefunction(args.func):
        code = run(args.func(args))
    else:
        code = args.func(args)

    if code is not None:
        sys.exit(code)


parser = ArgumentParser(description=__doc__)
parser.set_defaults(func=None)
parser.add_argument('-c', '--config', default=None, type=str,
                    help='file to read configuration from')

# Describe `connection` group.
g_log = parser.add_argument_group('logging options')
g_log.add_argument(
    '--log-level', default='info', choices=sorted(LOG_LEVELS.keys()),
    help='set logger verbosity level')
g_log.add_argument(
    '--log-output', default=stderr, metavar='FILENAME', type=FileType('w'),
    help='set output file or stderr (-) for logging')

# Describe subparsers for subcommands.
subparsers = parser.add_subparsers()

# Describe subcommand `announce`.
p_announce = subparsers.add_parser(
    'announce', help='send a broadcast message to users',
    description='Broadcast a notification message or news to a user.')
p_announce.set_defaults(func=announce)
p_announce.add_argument(
    '--dry-run', default=False, action=BooleanOptionalAction,
    help='actualy send nothing')
p_announce.add_argument('-o', '--output', type=Path,
                        help='path to file with sending statuses')
p_announce.add_argument('message', type=Path,
                        help='path to JSON-formatted message to send')
p_announce.add_argument('recipients', type=Path,
                        help='CSV-formatted mailing list')

# Describe subcommand `help`.
p_help = subparsers.add_parser('help', add_help=False,
                               help='show this message and exit')
p_help.set_defaults(func=help_)

# Describe subcommand `render`.
p_render = subparsers.add_parser(
    'render', help='render formula from command line')
p_render.set_defaults(func=render)

# Describe subcommand `serve`.
p_serve = subparsers.add_parser('serve', help='run telepyth services')
p_serve.set_defaults(func=serve)
p_serve_subparsers = p_serve.add_subparsers()

p_serve_api = p_serve_subparsers.add_parser('api', help='run rendering server')
p_serve_api.set_defaults(func=serve_api)
p_serve_api.add_argument('-d', '--root-dir', type=Path, default=Path('.'),
                         help='directory for compilation files')
p_serve_api.add_argument('-e', '--endpoint', type=str, help='service endpoint')
p_serve_api.add_argument('-i', '--interface', default='127.0.0.1',
                         help='interface to listen')
p_serve_api.add_argument('-p', '--port', default=8080,
                         help='interface to listen')

g_render = p_serve_api.add_argument_group('redering options')
g_render.add_argument(
    '--render-ppi', type=int, default=288, help='points per inch')
g_render.add_argument(
    '--render-margin', type=LengthType(), default='0.3em',
    help='space around equation (e.g. 0pt, 0.5em)')

p_serve_bot = p_serve_subparsers.add_parser('bot', help='run telegram bot')
p_serve_bot.set_defaults(func=serve_bot)
p_serve_bot.add_argument(
    '-e', '--endpoint', type=str, default='http://localhost:8080',
    help='rendering service endpoint')

# Describe subcommand `version`.
p_version = subparsers.add_parser('version', add_help=False,
                                  help='show version')
p_version.set_defaults(func=version)
