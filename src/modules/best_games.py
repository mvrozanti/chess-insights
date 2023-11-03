from functools import partial
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

from chess.pgn import read_game
from chess import WHITE, BLACK
from tqdm import tqdm

from common.db import make_db, fetch_game_from_db
from common.util import (
    make_game_generator,
    get_move_accuracy_for_game,
    count_user_games,
    get_user_color,
    color_as_string
)

from common.options import (
    username_option,
    color_option,
    limit_option,
    worker_count_option,
    remote_engines_option
)

def update_running_accuracy(username, hexdigest, game_accuracy):
    db.running_accuracy.insert_one({ 
        'username': username, 
        'hexdigest': hexdigest, 
        'game_accuracy': game_accuracy
        })

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    game_accuracies = {}
    game_count = count_user_games(db, args)
    game_generator = make_game_generator(db, args)
    with ThreadPoolExecutor(max_workers=args.worker_count) as executor:
        with tqdm(total=game_count*2, smoothing=False) as pbar:
            active_threads = set()
            def pop_future1(game_accuracies, player_color, hexdigest, future):
                move_accuracy = future.result()
                if len(move_accuracy) != 0:
                    game_accuracy = sum(move_accuracy) / len(move_accuracy)
                    if hexdigest not in game_accuracies:
                        game_accuracies[hexdigest] = {BLACK: None, WHITE: None}
                    game_accuracies[hexdigest][player_color] = game_accuracy
                    if all(game_accuracies[hexdigest].values()):
                        result = db.games.update_one({'hexdigest': hexdigest}, 
                                                {
                                                    '$set': { 
                                                        'white_accuracy': game_accuracies[hexdigest][WHITE],
                                                        'black_accuracy' : game_accuracies[hexdigest][BLACK]
                                                        },
                                                    '$addToSet': { 'tags': 'best_games'}
                                             })
                        if result.modified_count != 1:
                            raise AttributeError(f'Game {hexdigest} was not updated, with this game_accuracy pair: {game_accuracies[hexdigest]}')
                active_threads.remove(future)
                pbar.update(1)
            while True:
                try:
                    while len(active_threads) >= args.worker_count:
                        time.sleep(0.1)
                    game_document = next(game_generator)
                    pgn = game_document['pgn']
                    hexdigest = game_document['hexdigest']
                    game = read_game(StringIO(pgn))
                    user_color = get_user_color(username, game)
                    other_user = game.headers[color_as_string(not user_color).capitalize()]
                    other_user_color = not user_color
                    if 'best_games' in game_document['tags']:
                        game_accuracies[hexdigest] = {}
                        game_accuracies[hexdigest][WHITE] = game_document['white_accuracy']
                        game_accuracies[hexdigest][BLACK] = game_document['black_accuracy']
                        continue
                    pbar.set_description(f'Analyzing {hexdigest}')
                    pop_future_user = partial(pop_future1, game_accuracies, user_color, hexdigest)
                    pop_future_opponent = partial(pop_future1, game_accuracies, other_user_color, hexdigest)
                    future_user = executor.submit(get_move_accuracy_for_game,
                                             pgn,
                                             username)
                    future_opponent = executor.submit(get_move_accuracy_for_game,
                                             pgn,
                                             other_user)
                    active_threads.add(future_user)
                    active_threads.add(future_opponent)
                    future_user.add_done_callback(pop_future_user)
                    future_opponent.add_done_callback(pop_future_opponent)
                except StopIteration:
                    break
        while len(active_threads) > 0:
            time.sleep(0.1)
        if not game_accuracies:
            print(f'No games found in the database for {username}', file=sys.stderr)
            return None
        game_accuracies_filtered = {hexdigest: accuracies for hexdigest, accuracies in game_accuracies.items() if accuracies[True] and accuracies[False]}
        game_accuracies_sorted = sorted(game_accuracies_filtered.items(), key=lambda item: item[1][BLACK] + item[1][WHITE], reverse=True)
        complete_games_by_accuracy = []
        for idx, (hexdigest, accuracies) in enumerate(game_accuracies_sorted[:args.count]):
            game_document = fetch_game_from_db(db, hexdigest)
            game_accuracy = (game_document['white_accuracy'] + game_document['black_accuracy'])/2
            complete_games_by_accuracy.append({
                'link': game_document['headers']['Link'],
                'pgn': game_document['pgn'],
                'when': game_document['when'],
                'accuracy': game_accuracy,
            })
        db.client.close()
        return complete_games_by_accuracy

def add_subparser(action_name, subparsers):
    parser = subparsers.add_parser(action_name, help="returns the user's best games")
    username_option(parser)
    color_option(parser)
    limit_option(parser)
    worker_count_option(parser)
    remote_engines_option(parser)
    parser.add_argument(
        '-C',
        '--count',
        type=int,
        default=10,
        help='returns this amount of top games'
    )

