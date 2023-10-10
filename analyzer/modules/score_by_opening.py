from io import StringIO

from tqdm import tqdm
from chess.pgn import read_game

from common.db import make_db
from common.util import make_game_generator, count_user_games, get_result
from common.options import username_option, color_option, limit_option

def run(args):
    db = make_db()
    game_generator = make_game_generator(db, args)
    game_count = count_user_games(db, args)
    opening_scores = {}
    for game_document in tqdm(game_generator, total=game_count):
        pgn = game_document['pgn']
        game = read_game(StringIO(pgn))
        if 'ECO' not in game.headers:
            continue
        opening = game.headers['ECO']
        result = get_result(game, args.username)
        if opening not in opening_scores:
            opening_scores[opening] = 0
        opening_scores[opening] += result
    for opening, score in opening_scores.items():
        print(f'Opening {opening}: {score}')

def add_subparser(action_name, subparsers):
    score_by_opening_parser = subparsers.add_parser(
        action_name, help='identifies game score by opening')
    username_option(score_by_opening_parser)
    color_option(score_by_opening_parser)
    limit_option(score_by_opening_parser)
