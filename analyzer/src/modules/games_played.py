from io import StringIO

from tqdm import tqdm
from chess.pgn import read_game

from common.util import (
    make_game_generator,
    get_game_result,
    read_game,
    hash_pgn,
    count_user_games
)
from common.options import username_option, color_option, limit_option
from common.db import make_db

def fetch_summary_from_db(db, args):
    _filter = { 'username': args.username }
    games_played_summary = db.games_played_summary.find_one(_filter)
    if not games_played_summary:
        initialization = {
            'username': args.username,
            'summary': {},
            'hexdigests': []
        }
        return initialization
    return games_played_summary

def run(args):
    db = make_db()
    game_generator = make_game_generator(db, args)
    summary_document = fetch_summary_from_db(db, args)
    summary = summary_document['summary']
    hexdigests = summary_document['hexdigests']
    count = count_user_games(db, args)
    for game_document in tqdm(game_generator, total=count):
        pgn = game_document['pgn']
        hexdigest = hash_pgn(pgn)
        if hexdigest in hexdigests:
            continue
        game = read_game(StringIO(pgn))
        split_date = game.headers["Date"].split('.')
        year = split_date[0]
        month = split_date[1]
        if year not in summary:
            summary[year] = {}
        if month not in summary[year]:
            summary[year][month] = {'wins': 0, 'losses': 0, 'draws': 0}
        result = get_game_result(game, args.username)
        if result == 1:
            summary[year][month]['wins'] += 1
        if result == -1:
            summary[year][month]['losses'] += 1
        if result == 0.5:
            summary[year][month]['draws'] += 1
        hexdigests += [hexdigest]
    new_summary_document = {
        'username': args.username,
        'summary': summary,
        'hexdigests': hexdigests
    }
    db.games_played_summary.replace_one({
        'username': args.username, 
        }, new_summary_document, upsert=True)
    print(summary)
    return summary

def add_subparser(action_name, subparsers):
    games_played_parser = subparsers.add_parser(
        action_name, help='Summary of games played')
    username_option(games_played_parser)
    limit_option(games_played_parser)