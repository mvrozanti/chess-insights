#!/usr/bin/env python
import hashlib
from io import StringIO
from datetime import datetime
from collections import OrderedDict

from chess import WHITE, BLACK
from chess.pgn import read_game

from engine import make_engine
from remote_engine import set_remote_available
from db import make_db

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

def hash_pgn(pgn):
    return hashlib.md5(pgn.encode('utf-8')).hexdigest()

def make_game_generator(db, _filter):
    cursor = db.games.find(_filter).batch_size(10)
    try:
        for game_document in cursor:
            yield game_document
    finally:
        cursor.close()


def get_move_accuracy_for_game(pgn, username):
    db = make_db()
    move_accuracy_from_db = fetch_move_accuracy_from_db(db, hash_pgn(pgn), username)
    if move_accuracy_from_db and 'move_accuracy' in move_accuracy_from_db:
        return move_accuracy_from_db['move_accuracy']
    engine, limit, is_remote_engine = make_engine()
    move_accuracy = []
    game = read_game(StringIO(pgn))
    board = game.board()
    if username not in [game.headers['White'], game.headers['Black']]:
        raise LookupError(f'{username} not in game {hash_pgn(pgn)}')
    color = WHITE if game.headers['White'] == username else BLACK
    for actual_move in game.mainline_moves():
        if board.turn != color:
            board.push(actual_move)
            continue
        raw_move_accuracy = get_move_accuracy(db, board, engine, limit, actual_move, pgn)
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


def get_move_accuracy(db, board, engine, limit, actual_move, pgn):
    moves = {}
    for legal_move in board.legal_moves:
        fen = board.fen()
        eval_from_db = fetch_evaluation_from_db(db, fen, legal_move)
        if eval_from_db is not None:
            value = eval_from_db['evaluation']
        else:
            value = evaluate_move(board, engine, legal_move, limit)
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
    return raw_move_accuracy

def get_game_datetime(pgn):
    game = read_game(StringIO(pgn))
    game_date = game.headers['UTCDate']
    game_time = game.headers['UTCTime']
    date_format = "%Y.%m.%d %H:%M:%S"
    game_datetime = datetime.strptime(f'{game_date} {game_time}', date_format)
    return game_datetime
