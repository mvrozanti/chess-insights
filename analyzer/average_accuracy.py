from chess import WHITE, BLACK
from collections import OrderedDict
from engine import make_engine
from db import make_db
from io import StringIO
from chess.pgn import read_game
from tqdm import tqdm
import sys

def get_move_accuracy(game, color):
    engine, _, limit = make_engine()
    board = game.board()
    move_accuracy = []
    for actual_move_idx, actual_move in enumerate(game.mainline_moves()):
        if board.turn != color:
            board.push(actual_move)
            continue
        moves = {}
        for legal_move in board.legal_moves:
            info = engine.analyse(board, limit, root_moves=[legal_move])
            try:
                value = info['score'].relative.cp
            except:
                value = 10000 - info['score'].relative.mate()
                if info['score'].relative.mate() < 0:
                    value = -value
            if value not in moves:
                moves[value] = []
            moves[value].append(legal_move)
        ranked_moves = OrderedDict(sorted(moves.items(), key=lambda x: x[0], reverse=True))
        legal_move_count = len(ranked_moves)
        actual_move_rank = None
        for idx, moves in enumerate(ranked_moves.values()):
            if actual_move in moves:
                actual_move_rank = idx
                break
        raw_move_accuracy = (legal_move_count - actual_move_rank)/legal_move_count
        move_accuracy.append(raw_move_accuracy)
        board.push(actual_move)
    engine.quit()
    return move_accuracy

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    filter = {'username': username}
    game_documents = db.games.find(filter)
    game_count = db.games.count_documents(filter)
    game_accuracies = []
    for game_document in tqdm(game_documents, total=game_count):
        game = read_game(StringIO(game_document['pgn']))
        white_player = game.headers['White']
        black_player = game.headers['Black']
        user_color = WHITE if white_player == username else BLACK
        move_accuracy = get_move_accuracy(game, user_color)
        if not move_accuracy:
            print(f"Something is wrong with game {game_document['hexdigest']}")
            continue
        game_accuracy = sum(move_accuracy) / len(move_accuracy)
        game_accuracies += [game_accuracy]
    if not game_accuracies:
        print(f'No games found in the database for {username}', file=sys.stderr)
        return None
    average_accuracy = sum(game_accuracies) / len(game_accuracies)
    print('Average accuracy:', average_accuracy)
    return average_accuracy