#!/usr/bin/env python
from pymongo import TEXT
from pymongo import MongoClient

def __setup_db(db):
    db.games.create_index([('hexdigest', TEXT)], unique=True)
    db.move_analyses.create_index([('fen', TEXT), ('move', TEXT), ('gameHexdigest', TEXT)])
    db.move_accuracy_pgn_username.create_index(
        [
            ('fen', TEXT),
            ('move', TEXT),
            ('gameHexdigest', TEXT)
         ]
    )

def make_db():
    uri = 'mongodb://localhost:27017'
    client = MongoClient(uri)
    db = client['analyzer']
    __setup_db(db)
    return db
