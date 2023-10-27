import re
import sys
from io import StringIO

from chess import WHITE, BLACK
from chess.pgn import read_game
from tqdm import tqdm

from common.util import (
    make_game_generator, 
    fetch_move_accuracy_from_db, 
    hash_pgn, 
    count_user_games, 
    get_piece_repr
)
from common.db import make_db
from common.options import username_option, color_option, limit_option

def get_piece_accuracy_for_game(db, pgn, username):
    piece_accuracy = {}
    move_accuracy = fetch_move_accuracy_from_db(db, hash_pgn(pgn), username)
    if not move_accuracy:
        return {}
    game = read_game(StringIO(pgn))
    board = game.board()
    color = WHITE if game.headers['White'] == username else BLACK
    for actual_move_idx, actual_move in enumerate(game.mainline_moves()):
        if board.turn != color:
            board.push(actual_move)
            continue
        piece_repr = get_piece_repr(board, actual_move)
        if piece_repr not in piece_accuracy:
            piece_accuracy[piece_repr] = []
        piece_accuracy[piece_repr] += [move_accuracy[actual_move_idx//2]]
        board.push(actual_move)
    return piece_accuracy

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    game_count = count_user_games(db, args)
    piece_accuracy = {}
    for game_document in tqdm(make_game_generator(db, args), total=game_count):
        pgn = game_document['pgn']
        piece_accuracies_for_game = get_piece_accuracy_for_game(db, pgn, username)
        for piece_type, accuracies in piece_accuracies_for_game.items():
            if piece_type not in piece_accuracy:
                piece_accuracy[piece_type] = []
            piece_accuracy[piece_type] += accuracies
    for piece, accuracies in piece_accuracy.items():
        piece_accuracy[piece] = sum(accuracies)/len(accuracies)
    for piece, accuracy in piece_accuracy.items():
        print(f'{piece}: {accuracy*100:.2f}%')

def add_subparser(action_name, subparsers):
    move_accuracy_per_piece_parser = subparsers.add_parser(
        action_name, help='calculates average accuracy per piece for a user')
    username_option(move_accuracy_per_piece_parser)
    color_option(move_accuracy_per_piece_parser)
    limit_option(move_accuracy_per_piece_parser)
