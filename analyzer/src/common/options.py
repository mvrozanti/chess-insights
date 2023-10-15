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

