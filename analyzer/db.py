#!/usr/bin/env python
from util import hash_pgn
from pymongo import TEXT, ASCENDING

def __setup_db(db):
    games_collection = db.games
    db.games.create_index([('hexdigest', TEXT)], unique=True)

def make_db():
    from pymongo import MongoClient
    uri = 'mongodb://root:example@localhost:27017/admin?authSource=admin&authMechanism=SCRAM-SHA-1'
    client = MongoClient(uri)
    db = client['analyzer']
    __setup_db(db)
    return db