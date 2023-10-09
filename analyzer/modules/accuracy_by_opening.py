from io import StringIO

from tqdm import tqdm
from chess.pgn import read_game

from common.db import make_db
from common.util import make_game_generator, count_user_games, fetch_move_accuracy_from_db, hash_pgn

def run(args):
    db = make_db()
    game_generator = make_game_generator(db, args)
    game_count = count_user_games(db, args)
    opening_accuracy = {}
    actual_game_count = 0
    for game_document in tqdm(game_generator, total=game_count):
        pgn = game_document['pgn']
        move_accuracy = fetch_move_accuracy_from_db(db, hash_pgn(pgn), args.username)
        if not move_accuracy:
            continue
        game_accuracy = sum(move_accuracy)/len(move_accuracy)
        game = read_game(StringIO(pgn))
        if 'ECO' not in game.headers:
            continue
        opening = game.headers['ECO']
        if opening not in opening_accuracy:
            opening_accuracy[opening] = []
        opening_accuracy[opening] += [game_accuracy]
    for opening, accuracy in opening_accuracy.items():
        opening_accuracy[opening] = sum(accuracy)/len(accuracy)
    for opening, accuracy in opening_accuracy.items():
        print(f'Opening {opening}: {accuracy*100:.2f}%')

def add_subparser(action_name, subparsers):
    accuracy_by_opening_parser = subparsers.add_parser(
        action_name, help='identifies accuracy by opening')
    