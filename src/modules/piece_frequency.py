import re
import sys
from io import StringIO

from chess import WHITE, BLACK
from chess.pgn import read_game
from tqdm import tqdm

from common.util import make_game_generator, count_user_games
from common.db import make_db
from common.options import username_option, color_option, limit_option

def get_piece_frequency_for_game(pgn, username):
    piece_frequency = {}
    game = read_game(StringIO(pgn))
    board = game.board()
    color = WHITE if game.headers['White'] == username else BLACK
    for actual_move in game.mainline_moves():
        if board.turn != color:
            board.push(actual_move)
            continue
        piece_type = get_piece_type(board, actual_move)
        if piece_type not in piece_frequency:
            piece_frequency[piece_type] = 0
        piece_frequency[piece_type] += 1
        board.push(actual_move)
    return piece_frequency

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    game_count = count_user_games(db, args)
    piece_frequency = {}
    for game_document in tqdm(make_game_generator(db, args), total=game_count):
        pgn = game_document['pgn']
        piece_frequencies_for_game = get_piece_frequency_for_game(pgn, username)
        for piece_type, frequency in piece_frequencies_for_game.items():
            if piece_type not in piece_frequency:
                piece_frequency[piece_type] = 0
            piece_frequency[piece_type] += frequency

    total_sum = sum(piece_frequency.values())
    proportions = {key: value / total_sum for key, value in piece_frequency.items()}
    for piece, proportion in proportions.items():
        print(f'{piece}: {proportion*100:.2f}%')

def add_subparser(action_name, subparsers):
    average_accuracy_parser = subparsers.add_parser(
        action_name, help='calculates piece move frequency proportions')
    username_option(average_accuracy_parser)
    color_option(average_accuracy_parser)
    limit_option(average_accuracy_parser)
