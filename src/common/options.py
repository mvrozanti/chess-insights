import sys
from common.util import PIECES_STR
from datetime import datetime

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
        default=sys.maxsize,
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

def remote_engines_option(parser):
    parser.add_argument(
        '-r',
        '--remote-engines',
        default=[],
        nargs='*',
        help='use a remote engine in addition to local engines (format: USER@ADDRESS)'
    )

def pieces_option(parser):
    parser.add_argument(
        '-p',
        '--pieces',
        default=PIECES_STR,
        nargs='*',
        choices=PIECES_STR,
        help='filters by piece'
    )
    
def time_controls_option(parser):
    parser.add_argument(
        '--time-controls',
        default=[],
        nargs='*',
        help='filters by time control'
    )    
    
def variant_option(parser):
    parser.add_argument(
        '-v',
        '--variants',
        default=[],
        help='filters by variant'
    )
    
def date_range_options(parser):
    parser.add_argument(
        '--start-date',
        default=datetime.min,
        type=lambda s: datetime.strptime(s, "%Y-%m-%d"), 
        help="start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        '--end-date', 
        default=datetime.max,
        type=lambda s: datetime.strptime(s, "%Y-%m-%d"), 
        help="end date (YYYY-MM-DD)"
    )