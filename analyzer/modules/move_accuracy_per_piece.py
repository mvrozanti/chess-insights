import re
import sys
from io import StringIO

from chess import WHITE, BLACK
from chess.pgn import read_game
from tqdm import tqdm

from common.util import make_game_generator, fetch_move_accuracy_from_db, hash_pgn
from common.db import make_db

def get_piece_type(board, move):
    piece = re.sub('[^A-Z]', '', board.san(move))
    return piece if piece else 'p'

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
        piece_type = get_piece_type(board, actual_move)
        if piece_type not in piece_accuracy:
            piece_accuracy[piece_type] = []
        piece_accuracy[piece_type] += [move_accuracy[actual_move_idx//2]]
        board.push(actual_move)
    return piece_accuracy

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    _filter = {'username': username}
    game_count = db.games.count_documents(_filter)
    piece_accuracy = {}
    for game_document in tqdm(make_game_generator(db, _filter), total=game_count):
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
    average_accuracy_parser = subparsers.add_parser(
        action_name, help='Calculates average accuracy per piece for a user')
    average_accuracy_parser.add_argument(
        '-u',
        '--username',
        required=True
    )
