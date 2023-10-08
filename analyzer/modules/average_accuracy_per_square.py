import sys
import math
from io import StringIO
import re

from chess import WHITE, BLACK
from chess.pgn import read_game
from tqdm import tqdm

from common.util import make_game_generator, fetch_move_accuracy_from_db, hash_pgn
from common.db import make_db

def get_dest_square(move):
    file = chr((move.to_square % 8) + ord('a'))
    rank = (move.to_square // 8) + 1
    square = file + str(rank)
    return square

def get_square_accuracy_for_game(db, pgn, username):
    square_accuracy = {}
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
        dest_square = get_dest_square(board, actual_move)
        if dest_square not in square_accuracy:
            square_accuracy[dest_square] = []
        square_accuracy[dest_square] += [move_accuracy[actual_move_idx//2]]
        board.push(actual_move)
    return square_accuracy

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    _filter = {'username': username}
    game_count = db.games.count_documents(_filter)
    square_accuracy = {}
    for game_document in tqdm(make_game_generator(db, _filter, limit=args.limit), total=game_count):
        pgn = game_document['pgn']
        square_accuracies_for_game = get_square_accuracy_for_game(db, pgn, username)
        for square, accuracies in square_accuracies_for_game.items():
            if square not in square_accuracy:
                square_accuracy[square] = []
            square_accuracy[square] += accuracies
    for square, accuracies in square_accuracy.items():
        square_accuracy[square] = sum(accuracies)/len(accuracies)
    for square, accuracy in square_accuracy.items():
        print(f'{square}: {accuracy*100:.2f}%')

def add_subparser(action_name, subparsers):
    move_accuracy_per_piece_parser = subparsers.add_parser(
        action_name, help='Calculates average accuracy per square')
    move_accuracy_per_piece_parser.add_argument(
        '-u',
        '--username',
        required=True
    )
    move_accuracy_per_piece_parser.add_argument(
        '-l',
        '--limit',
        default=math.inf,
        type=int,
        help='limit of games to handle'
    )
