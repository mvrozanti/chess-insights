#!/usr/bin/env python
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from db import make_db
from util import get_game_datetime, hash_pgn

db = make_db()

def download_month(username, year, month):
    formatted_month = f'0{month}'if month < 10 else month
    url = f'http://api.chess.com/pub/player/{username}/games/{year}/{formatted_month}/pgn'
    headers = {
            'Content-type': 'text/plain',
            'User-Agent': 'curl/8.3.0',
            'Host': 'api.chess.com',
            'Accept': '*/*'
            }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        # print('Status code:', res.status_code)
        return None
    pgns = []
    raw_headers_and_games = res.text.split('\n\n')
    zipped_games = [list(pair) for pair in zip(raw_headers_and_games[::2], raw_headers_and_games[1::2])]
    for game_header, game in zipped_games:
        pgn = game_header + '\n\n' + game
        pgns += [pgn]
    return pgns

def download_all(username):
    cursor_date = datetime.now() - relativedelta(months=1)
    all_pgns = []
    while True:
        year = cursor_date.year
        month = cursor_date.month
        pgns = download_month(username, year, month)
        if not pgns:
            break
        all_pgns.extend(pgns) 
        for pgn in pgns:
            game_document = {
                    'pgn': pgn,
                    'when': get_game_datetime(pgn),
                    'username': username,
                    'hexdigest': hash_pgn(pgn)
                    }
            try:
                db.games.insert_one(game_document)
            except:
                break
        cursor_date = cursor_date - relativedelta(months=1)
    return all_pgns

if __name__ == '__main__':
    download_all('vegan_cheemsburger9000')