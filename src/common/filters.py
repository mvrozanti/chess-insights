from argparse import Namespace
from chess import WHITE, BLACK

def color_filter(args: Namespace) -> dict:
    _filter = {}
    if args.color == WHITE:
        _filter['headers.White'] = args.username
    elif args.color == BLACK:
        _filter['headers.Black'] = args.username
    return _filter

def date_filter(args: Namespace) -> dict:
    _filter = {}
    if hasattr(args, 'start_date'):
        _filter['when'] = {
            '$gte': args.start_date,
        }
    if hasattr(args, 'end_date'):
        _filter['when'] = {
            '$lte': args.end_date,
        }
    return _filter

def time_control_filter(args: Namespace) -> dict:
    _filter = {}
    if hasattr(args, 'time_controls') and args.time_controls:
        _filter['headers.TimeControl'] = {'$in': args.time_controls}
    return _filter

def variant_filter(args: Namespace) -> dict:
    _filter = {}
    if hasattr(args, 'variants') and args.variants:
        _filter['headers.Variant']  = {'$in': args.variants}
    return _filter

def merge_filters(args: Namespace) -> dict:
    _filter = {
        '$or': [
            { 'headers.Black': args.username }, 
            { 'headers.White': args.username }
        ]
    }
    _filter.update(color_filter(args))
    _filter.update(date_filter(args))
    _filter.update(time_control_filter(args))
    _filter.update(variant_filter(args))
    return _filter