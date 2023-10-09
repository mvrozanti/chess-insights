import sys
from io import StringIO

from chess import WHITE, BLACK
from chess.pgn import read_game
from tqdm import tqdm

from common.util import make_game_generator, fetch_move_accuracy_from_db, hash_pgn, count_user_games
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
        dest_square = get_dest_square(actual_move)
        if dest_square not in square_accuracy:
            square_accuracy[dest_square] = []
        square_accuracy[dest_square] += [move_accuracy[actual_move_idx//2]]
        board.push(actual_move)
    return square_accuracy

def plot_results(square_accuracy, username, actual_game_count):
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    chess_board = [[0] * 8 for _ in range(8)]
    for square, percentage in square_accuracy.items():
        col = ord(square[0]) - ord('a')
        row = int(square[1]) - 1
        chess_board[row][col] = percentage
    plt.figure(figsize=(8, 8))
    colors = [(1, 0, 0), (1, 0.5, 0.5), (1, 0.65, 0), (1, 1, 0), (0, 1, 0), (0, 1, 1)]
    cmap_name = 'red_cyan'
    custom_cmap = LinearSegmentedColormap.from_list(cmap_name, colors)
    plt.imshow(chess_board, cmap=custom_cmap, interpolation='nearest', aspect='auto')
    plt.colorbar(label='Accuracy (%)')
    plt.title(f'{username}\nSquare accuracy over {actual_game_count} games')
    plt.xticks(range(8), list('abcdefgh'))
    plt.yticks(range(8), list('12345678'))
    plt.gca().invert_yaxis()
    plt.show()

def run(args):
    if not args.username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    game_count = count_user_games(db, args)
    square_accuracy = {}
    actual_game_count = 0
    game_generator = make_game_generator(db, args)
    for game_document in tqdm(game_generator, total=game_count):
        pgn = game_document['pgn']
        square_accuracies_for_game = get_square_accuracy_for_game(db, pgn, args.username)
        for square, accuracies in square_accuracies_for_game.items():
            if square not in square_accuracy:
                square_accuracy[square] = []
            square_accuracy[square] += accuracies
        if square_accuracies_for_game:
            actual_game_count += 1
    for square, accuracies in square_accuracy.items():
        square_accuracy[square] = sum(accuracies)/len(accuracies)
    if args.plot:
        plot_results(square_accuracy, args.username, actual_game_count)
    else:
        for square, accuracy in square_accuracy.items():
            print(f'{square}: {accuracy*100:.2f}%')

def add_subparser(action_name, subparsers):
    move_accuracy_per_piece_parser = subparsers.add_parser(
        action_name, help='calculates average accuracy per square')
    move_accuracy_per_piece_parser.add_argument(
        '-p',
        '--plot',
        action='store_true'
    )
    