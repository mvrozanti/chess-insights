import sys
from io import StringIO
import pickle

from chess import WHITE, BLACK
from chess.pgn import read_game
from tqdm import tqdm
import numpy as np
from bson import Binary

from common.util import (
    make_game_generator,
    fetch_move_accuracy_from_db,
    hash_pgn,
    count_user_games,
    color_as_string,
    get_user_color_from_pgn,
    get_piece_type,
    get_piece_type_from_name,
    PIECES
)
from common.db import make_db
from common.options import username_option, color_option, limit_option, piece_option

def get_dest_square_coords(move):
    file = move.to_square % 8
    rank = move.to_square // 8
    return (file, rank)

def get_square_accuracy_for_game(db, pgn, username):
    square_accuracy = {
            piece_type: {
                'sum': np.zeros((8,8)),
                'len': np.zeros((8,8)) 
            } for piece_type in PIECES
        }
    move_accuracy = fetch_move_accuracy_from_db(db, hash_pgn(pgn), username)
    if not move_accuracy:
        return {}
    game = read_game(StringIO(pgn))
    board = game.board()
    color = WHITE if game.headers['White'] == username else BLACK
    for move_idx, move in enumerate(game.mainline_moves()):
        if board.turn != color:
            board.push(move)
            continue
        dest_square_coords = get_dest_square_coords(move)
        piece_type = get_piece_type(board, move)
        square_accuracy[piece_type]['sum'][dest_square_coords] += move_accuracy[move_idx//2]
        square_accuracy[piece_type]['len'][dest_square_coords] += 1
        board.push(move)
    return square_accuracy

def plot_results(accuracy_matrix, username, actual_game_count, color):
    plt.figure(figsize=(8, 8))
    colors = [(1, 0, 0), (1, 0.5, 0.5), (1, 0.65, 0),
              (1, 1, 0), (0, 1, 0), (0, 1, 1)]
    cmap_name = 'red_cyan'
    custom_cmap = LinearSegmentedColormap.from_list(cmap_name, colors)
    plt.imshow(accuracy_matrix, cmap=custom_cmap,
               interpolation='nearest', aspect='auto')
    plt.colorbar(label='Accuracy (%)')
    title = f"{username}\nsquare accuracy"
    if color is not None:
        title += f'\nwith the {color_as_string(color)} pieces'
    title += f'({actual_game_count} games)'
    plt.title(title)
    plt.xticks(range(8), list('abcdefgh'))
    plt.yticks(range(8), list('12345678'))
    plt.gca().invert_yaxis()
    plt.show()
    
def square_coords_to_index(square):
    file, rank = square[0], int(square[1])
    file_index = ord(file) - ord('a')
    rank_index = rank - 1
    return file_index + rank_index * 8

def square_accuracy_to_matrix(square_accuracy):
    matrix = [[None] * 8 for _ in range(8)]
    for square, accuracies in square_accuracy.items():
        index = square_coords_to_index(square)
        row = index // 8
        col = index % 8
        matrix[row][col] = sum(accuracies) / len(accuracies)
    return np.array(matrix)

def fetch_running_accuracy_per_square_for_user(db, args):
    _filter = { 'username': args.username }
    raw_running_accuracy_per_square = db.running_accuracy_per_square.find_one(_filter)
    if not raw_running_accuracy_per_square:
        initialization = {
            'username': args.username,
            
            'sum_white': {
                    piece_type: np.zeros((8,8)) for piece_type in PIECES
                },
            'len_white': {
                    piece_type: np.zeros((8,8)) for piece_type in PIECES
                },
            'games_white': [],
            
            'sum_black': {
                    piece_type: np.zeros((8,8)) for piece_type in PIECES
                },
            'len_black': {
                    piece_type: np.zeros((8,8)) for piece_type in PIECES
                },
            'games_black': []
        }
        return initialization
    running_accuracy_per_square = raw_running_accuracy_per_square
    running_accuracy_per_square['sum_white'] = pickle.loads(raw_running_accuracy_per_square['sum_white'])
    running_accuracy_per_square['len_white'] = pickle.loads(raw_running_accuracy_per_square['len_white'])
    running_accuracy_per_square['sum_black'] = pickle.loads(raw_running_accuracy_per_square['sum_black'])
    running_accuracy_per_square['len_black'] = pickle.loads(raw_running_accuracy_per_square['len_black'])
    return running_accuracy_per_square

def update_running_accuracy_per_square_for_user(db, args, running_accuracy_per_square):
    running_accuracy_per_square = dict(running_accuracy_per_square)
    running_accuracy_per_square['sum_white'] = Binary(pickle.dumps(running_accuracy_per_square['sum_white']))
    running_accuracy_per_square['sum_black'] = Binary(pickle.dumps(running_accuracy_per_square['sum_black']))
    running_accuracy_per_square['len_white'] = Binary(pickle.dumps(running_accuracy_per_square['len_white']))
    running_accuracy_per_square['len_black'] = Binary(pickle.dumps(running_accuracy_per_square['len_black']))
    db.running_accuracy_per_square.replace_one({
        'username': args.username, 
        }, running_accuracy_per_square, upsert=True)

def add_piece_matrices(sums, lens, pieces):
    sum = np.zeros((8,8))
    len = np.zeros((8,8))
    for piece_name in pieces:
        piece_type = get_piece_type_from_name(piece_name)
        sum += sums[piece_type].copy()
        len += lens[piece_type].copy()
    return sum, len

def run(args):
    if not args.username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    game_count = count_user_games(db, args)
    running_accuracy_per_square = fetch_running_accuracy_per_square_for_user(db, args)
    game_generator = make_game_generator(db, args)
    processed_games = running_accuracy_per_square['games_white'] + \
            running_accuracy_per_square['games_black']
    for game_document in tqdm(game_generator, total=game_count):
        pgn = game_document['pgn']
        hexdigest = hash_pgn(pgn)
        if hexdigest in processed_games:
            continue
        game_color = get_user_color_from_pgn(args.username, pgn)
        if args.color and args.color != game_color:
            continue
        square_accuracies_per_piece = get_square_accuracy_for_game(db, pgn, args.username)
        game_color_string = color_as_string(game_color)
        for piece_type, square_accuracy_matrix in square_accuracies_per_piece.items():
            running_accuracy_per_square[f'sum_{game_color_string}'][piece_type] = \
                running_accuracy_per_square[f'sum_{game_color_string}'][piece_type].copy() + \
                square_accuracy_matrix['sum']
            running_accuracy_per_square[f'len_{game_color_string}'][piece_type] = \
                running_accuracy_per_square[f'len_{game_color_string}'][piece_type].copy() + \
                square_accuracy_matrix['len']
            running_accuracy_per_square[f'games_{game_color_string}'] += [hexdigest]
    update_running_accuracy_per_square_for_user(db, args, running_accuracy_per_square)
    if args.color is not None:
        color_string = color_as_string(args.color)
        sum = np.zeros((8,8))
        for pieceType, matrix  in running_accuracy_per_square[f'sum_{color_string}'].items():
            sum += matrix
        len = np.zeros((8,8))
        for pieceType, matrix  in running_accuracy_per_square[f'len_{color_string}'].items():
            len += matrix
    else:
        sums = list(running_accuracy_per_square['sum_white'].values()) + \
            list(running_accuracy_per_square['sum_black'].values())
        lens = list(running_accuracy_per_square['len_white'].values()) + \
            list(running_accuracy_per_square['len_black'].values())
        sum, len = add_piece_matrices(sums, lens, args.piece)
    heatmap = np.where(len == 0, None, sum / len).tolist()
    return heatmap

def add_subparser(action_name, subparsers):
    move_accuracy_per_piece_parser = subparsers.add_parser(
        action_name, help='calculates average accuracy per square')
    username_option(move_accuracy_per_piece_parser)
    color_option(move_accuracy_per_piece_parser)
    limit_option(move_accuracy_per_piece_parser)
    piece_option(move_accuracy_per_piece_parser)
    move_accuracy_per_piece_parser.add_argument(
        '-P',
        '--plot',
        action='store_true'
    )
