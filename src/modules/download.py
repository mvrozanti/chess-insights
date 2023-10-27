from datetime import datetime
from base64 import b64decode

import requests
from tqdm import tqdm
from pymongo.errors import DuplicateKeyError

from dateutil.relativedelta import relativedelta

from common.db import make_db
from common.util import get_game_datetime, hash_pgn
from common.options import username_option, limit_option
from common.config import config

USER_AGENT = f'{config["downloader-user-agent-username"]}/chess-insights'

def download_month(username, year, month):
    formatted_month = f'0{month}' if month < 10 else month
    url = f'http://api.chess.com/pub/player/{username}/games/{year}/{formatted_month}/pgn'
    headers = {
            'Content-type': 'text/plain',
            'User-Agent': USER_AGENT,
            'Host': 'api.chess.com',
            'Accept': '*/*'
            }
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        # print('Status code:', res.status_code)
        return None
    pgns = []
    raw_headers_and_games = res.text.split('\n\n')
    for game_header, game in zip(raw_headers_and_games[::2], raw_headers_and_games[1::2]):
        pgn = game_header + '\n\n' + game
        pgns += [pgn]
    return pgns

def run(args):
    db = make_db()
    username = args.username
    cursor_date = datetime.now() - relativedelta(months=1)
    username = args.username
    all_pgns = []
    months_done = 0
    with tqdm() as pbar:
        while months_done < args.months and len(all_pgns) < args.limit:
            year = cursor_date.year
            month = cursor_date.month
            pgns = download_month(username, year, month)
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
                except DuplicateKeyError:
                    continue
            cursor_date = cursor_date - relativedelta(months=1)
            months_done += 1
            pbar.update(1)
    print(f'Downloaded {len(all_pgns)} games')
    return all_pgns

def add_subparser(action_name, subparsers):
    downloader_parser = subparsers.add_parser(
        action_name, help='downloads games en masse off the chess.com public API')
    username_option(downloader_parser)
    limit_option(downloader_parser)
    downloader_parser.add_argument(
        '-m',
        '--months',
        default=12,
        type=int,
        help='how many years back to download (defaults to a year)'
    )
