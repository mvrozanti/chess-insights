from io import StringIO

from tqdm import tqdm
from chess.pgn import read_game
from chess import WHITE, BLACK

from common.db import make_db
from common.util import make_game_generator, count_user_games

def get_result(game, username):
    color = WHITE if game.headers['White'] == username else BLACK
    result = 0.5
    if game.headers['Result'] == '1-0':
        result = 1 if color == WHITE else -1
    elif game.headers['Result'] == '0-1':
        result = 1 if color == BLACK else -1
    else:
        result = 0.5
    return result

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
    accuracy_by_opening_parser = subparsers.add_parser(
        action_name, help='identifies accuracy by opening')
