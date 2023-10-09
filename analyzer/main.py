#!/usr/bin/env python
import argparse
import importlib
import os

from chess import WHITE, BLACK

from common.db import make_db

MODULES_DIRECTORY = 'modules'

db = make_db()

def map_color(args):
    if args.color == 'white':
        args.color = WHITE
    if args.color == 'black':
        args.color = BLACK
    if args.color == 'any':
        args.color = None

def add_global_arguments(parser):
    parser.add_argument(
        '-c',
        '--color',
        default='any',
        choices=['white', 'black', 'any'],
        help='filters by color'
    )
    parser.add_argument(
        '-u',
        '--username',
        required=True
    )
    parser.add_argument(
        '-l',
        '--limit',
        type=int,
        help='limit of games to handle'
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='analyzer', description='Chess Analyzer')
    subparsers = parser.add_subparsers(dest='command', required=True)
    for filename in os.listdir(MODULES_DIRECTORY):
        if filename.endswith('.py'):
            module_name = filename[:-3]
            action_module = importlib.import_module(f'{MODULES_DIRECTORY}.{module_name}')
            action_module.add_subparser(module_name, subparsers)
    add_global_arguments(parser)
    args = parser.parse_args()
    map_color(args)
    importlib.import_module(f'{MODULES_DIRECTORY}.{args.command}').run(args)
