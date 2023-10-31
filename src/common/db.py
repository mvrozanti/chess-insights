from pymongo import TEXT, MongoClient
from pymongo.database import Database
from chess import Move

def __setup_db(db: Database) -> None:
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


def make_db(uri: str = 'mongodb://localhost:27017', db_name: str = 'analyzer') -> Database:
    client = MongoClient(uri)
    db = client[db_name]
    __setup_db(db)
    return db

def fetch_evaluation_from_db(db: Database, fen: str, move: Move) -> dict:
    return db.move_analyses.find_one({'fen': fen, 'move': move.uci()})

def fetch_game_from_db(db: Database, hexdigest: str) -> dict:
    return db.games.find_one({'hexdigest': hexdigest})

def fetch_move_accuracy_from_db(db: Database, hexdigest: str, username: str) -> dict:
    _filter = {'hexdigest': hexdigest, 'username': username}
    move_accuracy = db.move_accuracy_pgn_username.find_one(_filter)
    return move_accuracy['move_accuracy'] if move_accuracy else None
