#!/usr/bin/env python
from chess import WHITE, BLACK
from io import StringIO
from chess.pgn import read_game
from datetime import datetime
import argparse
from downloader import download_all
from db import make_db
import sys
from util import get_game_datetime, hash_pgn
from engine import make_engine

db = make_db()

def main(args):
    if args.analyze:
        __import__(args.analyze).run(args)
    if args.download_all:
        if not args.username:
            print('--download-all requires a --username argument', file=sys.stderr)
            exit(1)
        all_pgns = download_all(args.username)
        print(f'Downloaded {len(all_pgns)} pgns')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='analyzer', description='Chess Analyzer')
    parser.add_argument(
            '-f', '--from',
            type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
            default=datetime.min,
            required=False,
            help='filters games from this date'
    )
    parser.add_argument(
            '-t', '--to',
            type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
            default=datetime.max,
            required=False,
            help='filters games up to this date'
    )

    analyses = ['average_accuracy', 'move_accuracy_per_piece']
    parser.add_argument('--username')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--download-all', action='store_true')
    group.add_argument('--analyze', choices=analyses)
    args = parser.parse_args()
    main(args)
