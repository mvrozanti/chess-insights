#!/usr/bin/env python
from datetime import datetime
import argparse
import importlib
import os

from common.db import make_db

MODULES_DIRECTORY = 'modules'

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

    subparsers = parser.add_subparsers(dest='command', required=True)
    for filename in os.listdir(MODULES_DIRECTORY):
        if filename.endswith('.py'):
            module_name = filename[:-3]
            action_module = importlib.import_module(f'{MODULES_DIRECTORY}.{module_name}')
            action_module.add_subparser(module_name, subparsers)
    args = parser.parse_args()
    importlib.import_module(f'{MODULES_DIRECTORY}.{args.command}').run(args)
