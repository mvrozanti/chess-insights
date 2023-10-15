import sys
from io import StringIO
import pickle

from chess import WHITE, BLACK
from chess.pgn import read_game
from tqdm import tqdm
import numpy as np
from bson import Binary

from common.util import make_game_generator, \
    fetch_move_accuracy_from_db, \
    hash_pgn, \
    count_user_games, \
    color_as_string, \
    get_user_color_from_pgn
from common.db import make_db
from common.options import username_option, color_option, limit_option

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
        dest_square = get_dest_square(actual_move)
        if dest_square not in square_accuracy:
            square_accuracy[dest_square] = []
        square_accuracy[dest_square] += [move_accuracy[actual_move_idx//2]]
        board.push(actual_move)
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
            
            'sum_white': np.zeros((8,8)),
            'len_white': np.zeros((8,8)),
            'games_white': [],
            
            'sum_black': np.zeros((8,8)),
            'len_black': np.zeros((8,8)),
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
        square_accuracies_for_game = get_square_accuracy_for_game(
            db, pgn, args.username)
        square_accuracy_matrix = square_accuracy_to_matrix(square_accuracies_for_game)
        game_color_string = color_as_string(game_color)
        
        running_accuracy_per_square[f'sum_{game_color_string}'] = running_accuracy_per_square[f'sum_{game_color_string}'].copy() + \
            np.where(square_accuracy_matrix == None, 0, square_accuracy_matrix)
        square_accuracy_matrix_len = np.vectorize(lambda v: 1 if v is not None else 0)(square_accuracy_matrix)
        running_accuracy_per_square[f'len_{game_color_string}'] = running_accuracy_per_square[f'len_{game_color_string}'].copy() + square_accuracy_matrix_len
        running_accuracy_per_square[f'games_{game_color_string}'] += [hexdigest]
    update_running_accuracy_per_square_for_user(db, args, running_accuracy_per_square)
    if args.color:
        color_string = color_as_string(args.color)
        sum = running_accuracy_per_square['sum_{color_string}']
        len = running_accuracy_per_square['len_{color_string}']
    else:
        sum = running_accuracy_per_square['sum_white'] + \
            running_accuracy_per_square['sum_black']
        len = running_accuracy_per_square['len_white'] + \
            running_accuracy_per_square['len_black']
    heatmap = (sum / len).tolist()
    return heatmap

def add_subparser(action_name, subparsers):
    move_accuracy_per_piece_parser = subparsers.add_parser(
        action_name, help='calculates average accuracy per square')
    username_option(move_accuracy_per_piece_parser)
    color_option(move_accuracy_per_piece_parser)
    limit_option(move_accuracy_per_piece_parser)
    move_accuracy_per_piece_parser.add_argument(
        '-p',
        '--plot',
        action='store_true'
    )
