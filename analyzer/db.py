#!/usr/bin/env python
from util import hash_pgn
from pymongo import TEXT, ASCENDING

def __setup_db(db):
    games_collection = db.games
    move_analyses_collection = db.move_analyses
    db.games.create_index([('hexdigest', TEXT)], unique=True)
    db.move_analyses.create_index([('fen', TEXT), ('move', TEXT), ('gameHexdigest', TEXT)])
    db.move_accuracy_pgn_username.create_index([('fen', TEXT), ('move', TEXT), ('gameHexdigest', TEXT)])

def make_db():
    from pymongo import MongoClient
    uri = 'mongodb://mongo:chess-playground@localhost:27017/?authMechanism=DEFAULT'
    client = MongoClient(uri)
    db = client['analyzer']
    __setup_db(db)
    return db
