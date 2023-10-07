
from chess import WHITE, BLACK
from chess.pgn import read_game
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from db import make_db
from engine import make_engine
from functools import partial
from io import StringIO
from pymongo.errors import DuplicateKeyError
from tqdm import tqdm
from util import hash_pgn
from remote_engine import is_remote_available, set_remote_available
import sys
import time

def evaluate_move(board, engine, move, limit):
    info = engine.analyse(board, limit, root_moves=[move], multipv=1)
    try:
        value = info[0]['score'].relative.cp
    except:
        value = 10000 - info[0]['score'].relative.mate()
        if info[0]['score'].relative.mate() < 0:
            value = -value
    return value

def fetch_evaluation_from_db(db, fen, move):
    return db.move_analyses.find_one({'fen': fen, 'move': move.uci()})

def fetch_move_accuracy_from_db(db, hexdigest, username):
    return db.move_accuracy_pgn_username.find_one({'hexdigest': hexdigest, 'username': username})

def get_move_accuracy(pgn, username):
    db = make_db()
    move_accuracy_from_db = fetch_move_accuracy_from_db(db, hash_pgn(pgn), username)
    if move_accuracy_from_db and 'move_accuracy' in move_accuracy_from_db:
        return move_accuracy_from_db['move_accuracy']
    engine, limit, is_remote_engine = make_engine()
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
            fen = board.fen()
            eval_from_db = fetch_evaluation_from_db(db, fen, legal_move)
            value = eval_from_db['evaluation'] if eval_from_db is not None else evaluate_move(board, engine, legal_move, limit)
            move_analysis = {
                    'fen': fen,
                    'move': legal_move.uci(),
                    'evaluation': value,
                    'evalVersion': 1,
                    'gameHexdigest': hash_pgn(pgn)
                }
            if eval_from_db is None and legal_move == actual_move:
                db.move_analyses.insert_one(move_analysis)
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
    db.move_accuracy_pgn_username.insert_one({
        'hexdigest': hash_pgn(pgn),
        'username': username,
        'move_accuracy': move_accuracy
    })
    engine.close()
    if is_remote_engine:
        set_remote_available(True)
    return move_accuracy

def make_game_generator(db, filter):
    cursor = db.games.find(filter).batch_size(10)
    try:
        for game_document in cursor:
            yield game_document
    finally:
        cursor.close()

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    filter = {'username': username}
    game_accuracies = []
    game_count = db.games.count_documents(filter)
    game_generator = make_game_generator(db, filter)
    CONCURRENCY = 16 # rule of thumb: at most, number of logical cores
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        with tqdm(total=game_count, smoothing=False) as pbar:
            active_threads = set()
            def pop_future1(game_accuracies, future):
                try:
                    move_accuracy = future.result()
                    if len(move_accuracy) != 0:
                        game_accuracy = sum(move_accuracy) / len(move_accuracy)
                        game_accuracies += [game_accuracy]
                except Exception as e:
                    if 'engine process died' not in str(e):
                        print(e)
                active_threads.remove(future)
                pbar.update(1)
            pop_future2 = partial(pop_future1, game_accuracies)
            while True:
                try:
                    while len(active_threads) == CONCURRENCY:
                        time.sleep(0.1)
                    game_document = next(game_generator)
                    pbar.set_description(f'Analyzing {game_document["hexdigest"]}')
                    future = executor.submit(get_move_accuracy, game_document['pgn'], username)
                    active_threads.add(future)
                    future.add_done_callback(pop_future2)
                except StopIteration:
                    break
        while len(active_threads) > 0:
            time.sleep(0.1)
        if not game_accuracies:
            print(f'No games found in the database for {username}', file=sys.stderr)
            return None
        average_accuracy = sum(game_accuracies) / len(game_accuracies)
        print(f'Average accuracy: {average_accuracy*100:.2f}%')
        return average_accuracy