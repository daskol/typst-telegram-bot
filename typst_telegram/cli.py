import logging
import sys
from argparse import ArgumentParser, ArgumentTypeError, FileType, Namespace
from asyncio import run
from inspect import iscoroutinefunction
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


def render(ns: Namespace):
    raise NotImplementedError


def help_(args: Namespace):
    parser.print_help()


def serve(ns: Namespace):
    raise RuntimeError('Unreachable execution branch.')


def serve_api(ns: Namespace):
    if ns.endpoint is None:
        ns.endpoint = f'http://{ns.interface}:{ns.port}'
        logging.info('no endpoint specified: infer it from arguments: %s',
                     ns.endpoint)
    from typst_telegram.api import serve
    kwargs = vars(ns)
    return serve(host=kwargs.pop('interface'),
                 port=kwargs.pop('port'),
                 **kwargs)


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

# Describe subcommand `help`.
p_help = subparsers.add_parser('help', add_help=False,
                               help='show this message and exit')
p_help.set_defaults(func=help_)

# Describe subcommand `render`.
p_render = subparsers.add_parser('render',
    help='render formula from command line')
p_render.set_defaults(func=render)

# Describe subcommand `serve`.
p_serve = subparsers.add_parser('serve', help='run telepyth services')
p_serve.set_defaults(func=serve)
p_serve_subparsers = p_serve.add_subparsers()

p_serve_api = p_serve_subparsers.add_parser('api', help='run rendering server')
p_serve_api.set_defaults(func=serve_api)
p_serve_api.add_argument('-i', '--interface', default='127.0.0.1',
                         help='interface to listen')
p_serve_api.add_argument('-p', '--port', default=8080,
                         help='interface to listen')
p_serve_api.add_argument('-e', '--endpoint', type=str, help='service endpoint')

p_serve_bot = p_serve_subparsers.add_parser('bot', help='run telegram bot')
p_serve_bot.set_defaults(func=serve_bot)
p_serve_bot.add_argument(
    '-e', '--endpoint', type=str, default='http://localhost:8080',
    help='rendering service endpoint')

# Describe subcommand `version`.
p_version = subparsers.add_parser('version', add_help=False,
                                  help='show version')
p_version.set_defaults(func=version)
