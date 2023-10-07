#!/usr/bin/env python
from datetime import datetime
import argparse
from db import make_db

db = make_db()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='analyzer', description='Chess Analyzer')
    parser.add_argument(
        '-s', '--start',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        default=datetime.min,
        required=False,
        help='filters games from this date'
    )
    parser.add_argument(
        '-e', '--end',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        default=datetime.max,
        required=False,
        help='filters games up to this date'
    )

    actions = ['download', 'average_accuracy', 'move_accuracy_per_piece']
    subparsers = parser.add_subparsers(dest='command')
    for action_name in actions:
        __import__(action_name).add_subparser(action_name, subparsers)
    args = parser.parse_args()
    __import__(args.command).run(args)
    