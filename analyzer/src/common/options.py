def username_option(parser, required=True):
    parser.add_argument(
        '-u',
        '--username',
        required=required
    )

def color_option(parser):
    parser.add_argument(
        '-c',
        '--color',
        default='any',
        choices=['white', 'black', 'any'],
        help='filters by color'
    )

def limit_option(parser):
    parser.add_argument(
        '-l',
        '--limit',
        type=int,
        help='limit of games to handle'
    )

def worker_count_option(parser):
    parser.add_argument(
        '-w',
        '--worker-count',
        default=4,
        type=int,
        help='how many workers to have running concurrently'
    )

def remote_engine_option(parser):
    parser.add_argument(
        '-r',
        '--remote-engine',
        help='use a remote engine in addition to local engines (format: USER@ADDRESS)'
    )