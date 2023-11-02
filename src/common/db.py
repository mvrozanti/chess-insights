from pymongo import TEXT, MongoClient
from pymongo.database import Database
from pymongo.collation import Collation
from chess import Move

def __setup_games(db: Database):
    db.games.create_index([
        ('hexdigest', TEXT)
    ], unique=True)
    db.games.create_index([
        ('headers.White', 1),
        ('headers.Black', 1),
        ('headers.Result', 1),
        ('headers.ECO', 1),
        ('headers.TimeControl', 1),
        ('headers.Termination', 1),
        ('headers.Variant', 1),
    ])
    db.games.create_index([("headers.White", 1)], collation=collation())
    db.games.create_index([("headers.Black", 1)], collation=collation())
    
def __setup_db(db: Database) -> None:
    __setup_games(db)
    db.move_accuracy.create_index([
            ('gameHexdigest', TEXT),
            ('username', TEXT)
         ])
    db.accuracy_per_square.create_index([
            ('username', TEXT)
         ], unique = True)
    
    db.games_played_summary.create_index([
            ('username', TEXT)
         ], unique = True)

def make_db(uri: str = 'mongodb://localhost:27017', db_name: str = 'chess-insights') -> Database:
    client = MongoClient(uri)
    db = client[db_name]
    __setup_db(db)
    return db

def fetch_game_from_db(db: Database, hexdigest: str) -> dict:
    return db.games.find_one({'hexdigest': hexdigest})

def fetch_move_accuracy_from_db(db: Database, hexdigest: str, username: str) -> dict:
    move_accuracy = db.move_accuracy.find_one({
            'hexdigest': hexdigest, 
            'username': username
        })
    return move_accuracy['move_accuracy'] if move_accuracy else None

def collation():
    return Collation(locale='en', strength=2)