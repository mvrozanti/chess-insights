#!/usr/bin/env python
import hashlib
from io import StringIO
from chess.pgn import read_game
from datetime import datetime

def hash_pgn(pgn):
    return hashlib.md5(pgn.encode('utf-8')).hexdigest()

def get_game_datetime(pgn):
    game = read_game(StringIO(pgn))
    game_date = game.headers['UTCDate']
    game_time = game.headers['UTCTime']
    date_format = "%Y.%m.%d %H:%M:%S"
    game_datetime = datetime.strptime(f'{game_date} {game_time}', date_format)
    return game_datetime
