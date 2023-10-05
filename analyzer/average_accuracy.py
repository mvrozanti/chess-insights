from chess import WHITE, BLACK
from collections import OrderedDict
from engine import make_engine
from db import make_db
from io import StringIO
from chess.pgn import read_game
from tqdm import tqdm
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_move_accuracy(pgn, username):
    engine, limit = make_engine()
    move_accuracy = []
    game = read_game(StringIO(pgn))
    board = game.board()
    white_player = game.headers['White']
    black_player = game.headers['Black']
    color = WHITE if white_player == username else BLACK
    for actual_move_idx, actual_move in enumerate(game.mainline_moves()):
        if board.turn != color:
            board.push(actual_move)
            continue
        moves = {}
        for legal_move in board.legal_moves:
            info = engine.analyse(board, limit, root_moves=[legal_move], multipv=1)
            try:
                value = info[0]['score'].relative.cp
            except:
                e = 10000 - info[0]['score'].relative.mate()
                if info[0]['score'].relative.mate() < 0:
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
    engine.close()
    return move_accuracy

def game_generator(db, filter):
    for game_document in db.games.find(filter).limit(60):
        yield game_document

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    filter = {'username': username}
    game_accuracies = []
    game_count = db.games.count_documents(filter)
    with ThreadPoolExecutor(max_workers=3) as executor:
        with tqdm(total=game_count) as pbar:
            futures = [executor.submit(get_move_accuracy, game_document['pgn'], username) for game_document in game_generator(db, filter)]
            for future in as_completed(futures):
                move_accuracy = future.result()
                game_accuracy = sum(move_accuracy) / len(move_accuracy)
                game_accuracies += [game_accuracy]
                pbar.update(1)
            if not game_accuracies:
                print(f'No games found in the database for {username}', file=sys.stderr)
                return None
            average_accuracy = sum(game_accuracies) / len(game_accuracies)
            print('Average accuracy:', average_accuracy)
            return average_accuracy