import hashlib
from io import StringIO
from datetime import datetime
from collections import OrderedDict
import sys
import os
from importlib import import_module

from chess import WHITE, BLACK
from chess.pgn import read_game
from chess.engine import INFO_SCORE, EngineTerminatedError

from .engine import make_engine, limit
from .remote_engine import set_remote_available
from .db import make_db

MODULES = list(
    map(lambda f: f[:-3],
        filter(lambda f: f.endswith('.py'),
               os.listdir('modules')
            )
        )
    )

def load_module(module):
    return import_module(f'modules.{module}')

def evaluate_move(board, engine, move):
    info = engine.analyse(board, limit(), root_moves=[move], multipv=1, info=INFO_SCORE)
    relative_eval = info[0]['score'].relative
    if relative_eval.is_mate():
        value = 10000 - info[0]['score'].relative.mate()
        if info[0]['score'].relative.mate() < 0:
            value = -value
    else:
        value = relative_eval.cp
    return value

def fetch_evaluation_from_db(db, fen, move):
    return db.move_analyses.find_one({'fen': fen, 'move': move.uci()})

def fetch_move_accuracy_from_db(db, hexdigest, username):
    _filter = {'hexdigest': hexdigest, 'username': username}
    move_accuracy = db.move_accuracy_pgn_username.find_one(_filter)
    return move_accuracy['move_accuracy'] if move_accuracy else None

def hash_pgn(pgn):
    return hashlib.md5(pgn.encode('utf-8')).hexdigest()

def color_filter(username, color=None):
    _filter = {}
    if color == WHITE:
        _filter['pgn'] = {'$regex':f'.*White "{username}".*'}
    elif color == BLACK:
        _filter['pgn'] = {'$regex':f'.*Black "{username}".*'}
    return _filter

def get_result(game, username):
    color = WHITE if game.headers['White'] == username else BLACK
    result = 0.5
    if game.headers['Result'] == '1-0':
        result = 1 if color == WHITE else -1
    elif game.headers['Result'] == '0-1':
        result = 1 if color == BLACK else -1
    else:
        result = 0.5
    return result

def color_as_string(color):
    if color is True:
        return 'white'
    if color is False:
        return 'black'
    raise ValueError()

def count_user_games(db, args):
    _filter = {'username': args.username}
    _filter.update(color_filter(args.username, args.color))
    return db.games.count_documents(_filter)

def make_game_generator(db, args):
    _filter = {'username': args.username}
    _filter.update(color_filter(args.username, args.color))
    cursor = db.games.find(_filter).batch_size(10)
    if args.limit is not None:
        cursor = cursor.limit(args.limit)
    try:
        for game_document in cursor:
            yield game_document
    finally:
        cursor.close()

def get_move_accuracy_for_game(pgn, username, remote_engine):
    db = make_db()
    move_accuracy_from_db = fetch_move_accuracy_from_db(db, hash_pgn(pgn), username)
    if move_accuracy_from_db:
        return move_accuracy_from_db
    engine, is_remote_engine = make_engine(remote=remote_engine)
    move_accuracy = []
    game = read_game(StringIO(pgn))
    board = game.board()
    color = WHITE if game.headers['White'] == username else BLACK
    for actual_move in game.mainline_moves():
        if board.turn != color:
            board.push(actual_move)
            continue
        try:
            raw_move_accuracy = get_move_accuracy(db, board, engine, actual_move, pgn)
            move_accuracy.append(raw_move_accuracy)
            board.push(actual_move)
        except EngineTerminatedError as e:
            if 'engine process died' not in str(e):
                print(e)
                sys.exit(1)
            elif is_remote_engine:
                set_remote_available(True)
            return []
    db.move_accuracy_pgn_username.insert_one({
        'hexdigest': hash_pgn(pgn),
        'username': username,
        'move_accuracy': move_accuracy
    })
    db.client.close()
    engine.close()
    if is_remote_engine:
        set_remote_available(True)
    return move_accuracy


def get_move_accuracy(db, board, engine, actual_move, pgn):
    moves = {}
    for legal_move in board.legal_moves:
        eval_from_db = fetch_evaluation_from_db(db, board.fen(), legal_move)
        if eval_from_db is not None:
            value = eval_from_db['evaluation']
        else:
            value = evaluate_move(board, engine, legal_move)
        move_analysis = {
                'fen': board.fen(),
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
    return raw_move_accuracy

def get_game_datetime(pgn):
    game = read_game(StringIO(pgn))
    game_date = game.headers['UTCDate']
    game_time = game.headers['UTCTime']
    date_format = "%Y.%m.%d %H:%M:%S"
    game_datetime = datetime.strptime(f'{game_date} {game_time}', date_format)
    return game_datetime
