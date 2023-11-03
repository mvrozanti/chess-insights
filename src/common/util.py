import hashlib
from io import StringIO
from datetime import datetime
from collections import OrderedDict
import sys
import os
from importlib import import_module
from argparse import Namespace
import re
from typing import Generator
from types import ModuleType

from chess import (
    WHITE,
    BLACK,
    PAWN,
    KNIGHT,
    BISHOP,
    ROOK,
    QUEEN,
    KING,
    PieceType,
    Board,
    Move
)
from chess.pgn import read_game, Game
from chess.engine import INFO_SCORE, EngineTerminatedError, SimpleEngine
from chess.pgn import StringExporter
from pymongo.database import Database

from .engine import make_engine, limit
from .remote_engine import set_remote_available
from .db import make_db, fetch_move_accuracy_from_db, collation
from .filters import merge_filters

PIECES = [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]
PIECES_STR = ['pawn', 'knight', 'bishop', 'rook', 'queen', 'king']

MODULES = list(
    map(lambda f: f[:-3],
        filter(lambda f: f.endswith('.py'),
               os.listdir('src/modules')
            )
        )
    )

def get_piece_name_from_type(piece_type: PieceType):
    return {
        PAWN: 'pawn',
        KNIGHT: 'knight',
        BISHOP: 'bishop',
        ROOK: 'rook',
        QUEEN: 'queen',
        KING: 'king'
    }[piece_type]

def get_piece_type_from_name(piece_name: str) -> PieceType:
    return {
        'pawn': PAWN,
        'knight': KNIGHT,
        'bishop': BISHOP,
        'rook': ROOK,
        'queen': QUEEN,
        'king': KING
    }[piece_name]

def get_piece_repr(board: Board, move: Move) -> str:
    piece = re.sub('[^A-Z]', '', board.san(move))
    return piece if piece else 'P'

def get_piece_type(board, move) -> PieceType:
    piece_repr = get_piece_repr(board, move)
    return {
        'P': PAWN,
        'N': KNIGHT,
        'B': BISHOP,
        'R': ROOK,
        'Q': QUEEN,
        'K': KING,
        'OO': KING,
        'OOO': KING,
    }[piece_repr]

def map_color_option(args: Namespace) -> Namespace:
    if not hasattr(args, 'color'):
        args.color = 'any'
        return args
    if args.color == 'white':
        args.color = WHITE
    if args.color == 'black':
        args.color = BLACK
    if args.color == 'any':
        args.color = None
    return args

def map_pieces_option(args: Namespace) -> Namespace:
    if not hasattr(args, 'pieces'):
        args.pieces = PIECES
    return args

def load_module(module: str) -> ModuleType:
    return import_module(f'modules.{module}', 'src')

def evaluate_move(board: Board, engine: SimpleEngine, move: Move) -> float:
    info = engine.analyse(board, limit(), root_moves=[move], multipv=1, info=INFO_SCORE)
    relative_eval = info[0]['score'].relative
    if relative_eval.is_mate():
        value = 10000 - info[0]['score'].relative.mate()
        if info[0]['score'].relative.mate() < 0:
            value = -value
    else:
        value = relative_eval.cp
    return value

def hash_pgn(pgn: str) -> str:
    return hashlib.md5(pgn.encode('utf-8')).hexdigest()

def get_game_result(game: Game, username: str) -> float:
    color = WHITE if game.headers['White'] == username else BLACK
    result = 0.5
    if game.headers['Result'] == '1-0':
        result = 1 if color == WHITE else -1
    elif game.headers['Result'] == '0-1':
        result = 1 if color == BLACK else -1
    else:
        result = 0.5
    return result

def string_as_color(string: str) -> bool:
    if string.lower() == 'white':
        return WHITE
    if string.lower() == 'black':
        return BLACK
    raise ValueError()

def color_as_string(color: bool) -> str:
    if color is WHITE:
        return 'white'
    if color is BLACK:
        return 'black'
    raise ValueError()

def count_user_games(db: Database, args: Namespace) -> int:
    _filter = merge_filters(args)
    document_count = db.games.count_documents(_filter, collation=collation())
    return document_count

def make_game_generator(db: Database, args: Namespace) -> Generator[dict, None, None]:
    _filter = merge_filters(args)
    _filter.update({'invalid': { '$exists': False }})
    cursor = db.games.find(_filter, collation=collation()).batch_size(10)
    if args.limit is not None:
        cursor = cursor.limit(args.limit)
    try:
        for game_document in cursor:
            yield game_document
    finally:
        cursor.close()

def get_move_accuracy_for_game(pgn: str, username: str) -> list[float]:
    db = make_db()
    hexdigest = hash_pgn(pgn)
    move_accuracy_from_db = fetch_move_accuracy_from_db(db, hexdigest, username)
    if move_accuracy_from_db:
        return move_accuracy_from_db
    engine, remote = make_engine()
    move_accuracy = []
    game = read_game(StringIO(pgn))
    board = game.board()
    color = get_user_color(username, game)
    for actual_move in game.mainline_moves():
        if board.turn != color:
            board.push(actual_move)
            continue
        try:
            raw_move_accuracy = get_move_accuracy(db, board, engine, actual_move, pgn)
            move_accuracy.append(raw_move_accuracy)
            board.push(actual_move)
        except EngineTerminatedError as e:
            db.games.update_one({'hexdigest': hexdigest}, {"$set": { 'invalid': True }})
            if 'engine process died' not in str(e):
                print(e)
                sys.exit(1)
            elif remote:
                set_remote_available(remote, True)
            return []
    db.move_accuracy.insert_one({
        'hexdigest': hexdigest,
        'username': username,
        'move_accuracy': move_accuracy
    })
    result = db.games.update_one({'hexdigest': hexdigest}, {'$addToSet': { 'tags': 'accuracy'}})
    if result.modified_count != 1 and len(move_accuracy) > 0:
        raise AttributeError(f'Game {hexdigest} was not updated')
    db.client.close()
    engine.close()
    if remote:
        set_remote_available(remote, True)
    return move_accuracy

def get_move_accuracy(db: Database, board: Board, engine: SimpleEngine, move: Move, pgn: str) -> float:
    moves = {}
    for legal_move in board.legal_moves:
        value = evaluate_move(board, engine, legal_move)
        if value not in moves:
            moves[value] = []
        moves[value].append(legal_move)
    ranked_moves = OrderedDict(sorted(moves.items(), key=lambda x: x[0], reverse=True))
    legal_move_count = len(ranked_moves)
    actual_move_rank = None
    for idx, moves in enumerate(ranked_moves.values()):
        if move in moves:
            actual_move_rank = idx
            break
    raw_move_accuracy = (legal_move_count - actual_move_rank)/legal_move_count
    return raw_move_accuracy

def get_game_datetime(pgn: str) -> datetime:
    game = read_game(StringIO(pgn))
    game_date = game.headers['UTCDate']
    game_time = game.headers['UTCTime']
    date_format = "%Y.%m.%d %H:%M:%S"
    game_datetime = datetime.strptime(f'{game_date} {game_time}', date_format)
    return game_datetime

def get_user_color_from_pgn(username: str, pgn: str) -> bool:
    match_white = re.match('.*White "(.+?)".*', pgn, re.DOTALL)
    match_black = re.match('.*Black "(.+?)".*', pgn, re.DOTALL)
    if match_white and match_white.group(1).lower() == username.lower():
        return WHITE
    if match_black and match_black.group(1).lower() == username.lower():
        return BLACK
    raise ValueError(f'Unknown value: \n{pgn}')

def get_user_color(username: str, game: Game) -> bool:
    if game.headers['White'] == username:
        return WHITE
    if game.headers['Black'] == username:
        return BLACK
    raise ValueError("Username doesn't match either color: ", username, game.headers['Link'])
