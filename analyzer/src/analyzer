#!/usr/bin/env python
from argparse import ArgumentParser

from chess import WHITE, BLACK

from common.util import MODULES, load_module

def map_color_option(args):
    if not hasattr(args, 'color'):
        return
    if args.color == 'white':
        args.color = WHITE
    if args.color == 'black':
        args.color = BLACK
    if args.color == 'any':
        args.color = None

def add_module_subparsers(parser):
    subparsers = parser.add_subparsers(dest='command', required=True)
    for module in MODULES:
        action_module = load_module(module)
        action_module.add_subparser(module, subparsers)

if __name__ == '__main__':
    parser = ArgumentParser(
        prog='analyzer', description='Chess Analyzer')
    add_module_subparsers(parser)
    args = parser.parse_args()
    map_color_option(args)
    load_module(args.command).run(args)
