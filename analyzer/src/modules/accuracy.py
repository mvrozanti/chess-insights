from functools import partial
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm

from common.db import make_db
from common.util import make_game_generator, get_move_accuracy_for_game, count_user_games
from common.options import username_option, color_option, limit_option

def run(args):
    username = args.username
    if not username:
        print('Username is required', file=sys.stderr)
    db = make_db()
    game_accuracies = []
    game_count = count_user_games(db, args)
    game_generator = make_game_generator(db, args)
    with ThreadPoolExecutor(max_workers=args.worker_count) as executor:
        with tqdm(total=game_count, smoothing=False) as pbar:
            active_threads = set()
            def pop_future1(game_accuracies, future):
                move_accuracy = future.result()
                if len(move_accuracy) != 0:
                    game_accuracy = sum(move_accuracy) / len(move_accuracy)
                    game_accuracies += [game_accuracy]
                active_threads.remove(future)
                pbar.update(1)
            pop_future2 = partial(pop_future1, game_accuracies)
            while True:
                try:
                    while len(active_threads) == args.worker_count:
                        time.sleep(0.1)
                    game_document = next(game_generator)
                    pbar.set_description(f'Analyzing {game_document["hexdigest"]}')
                    future = executor.submit(get_move_accuracy_for_game,
                                             game_document['pgn'],
                                             username,
                                             args.remote_engine)
                    active_threads.add(future)
                    future.add_done_callback(pop_future2)
                except StopIteration:
                    break
        db.client.close()
        while len(active_threads) > 0:
            time.sleep(0.1)
        if not game_accuracies:
            print(f'No games found in the database for {username}', file=sys.stderr)
            return None
        games_analyzed = len(game_accuracies)
        average_accuracy = sum(game_accuracies) / games_analyzed
        print(f'Games analyzed: {games_analyzed}')
        print(f'Average accuracy: {average_accuracy*100:.2f}%')
        return average_accuracy

def add_subparser(action_name, subparsers):
    average_accuracy_parser = subparsers.add_parser(
        action_name, help='calculates average accuracy for a user')
    username_option(average_accuracy_parser)
    color_option(average_accuracy_parser)
    limit_option(average_accuracy_parser)
    average_accuracy_parser.add_argument(
        '-r',
        '--remote-engine',
        help='use a remote engine in addition to local engines (format: USER@ADDRESS)'
    )
    average_accuracy_parser.add_argument(
        '-w',
        '--worker-count',
        default=4,
        type=int,
        help='how many workers to have running concurrently'
    )