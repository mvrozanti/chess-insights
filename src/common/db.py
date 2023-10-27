from pymongo import TEXT
from pymongo import MongoClient

def __setup_db(db):
    db.games.create_index([
        ('hexdigest', TEXT)
        ], unique=True)
    db.move_analyses.create_index([
        ('fen', TEXT), 
        ('move', TEXT), 
        ('gameHexdigest', TEXT)
    ])
    db.move_accuracy_pgn_username.create_index([
            ('fen', TEXT),
            ('move', TEXT),
            ('gameHexdigest', TEXT)
         ])
    db.running_accuracy.create_index([
            ('hexdigest', TEXT),
            ('username', TEXT)
         ])
    db.running_accuracy_per_square.create_index([
            ('username', TEXT)
         ], unique = True)
    db.games_played_summary.create_index([
            ('username', TEXT)
         ], unique = True)


def make_db(uri='mongodb://localhost:27017', db_name='analyzer'):
    client = MongoClient(uri)
    db = client[db_name]
    __setup_db(db)
    return db

def fetch_evaluation_from_db(db, fen, move):
    return db.move_analyses.find_one({'fen': fen, 'move': move.uci()})

def fetch_game_from_db(db, hexdigest):
    return db.games.find_one({'hexdigest': hexdigest})

def fetch_move_accuracy_from_db(db, hexdigest, username):
    _filter = {'hexdigest': hexdigest, 'username': username}
    move_accuracy = db.move_accuracy_pgn_username.find_one(_filter)
    return move_accuracy['move_accuracy'] if move_accuracy else None
