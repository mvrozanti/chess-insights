#!/usr/bin/env python
# https://chess.stackexchange.com/questions/28248/python-script-to-let-stockfish-selfplay-10-games-from-a-given-position
from chess import Board
from chess.engine import SimpleEngine, Limit
from chess.pgn import Game, FileExporter
import os
import sys
import collections
import random
from datetime import datetime
from time import time
from threading import Thread

def make_engine():
    elo = random.randint(2850,2850)
    engine = SimpleEngine.popen_uci('stockfish')
    engine.configure({'UCI_LimitStrength': True})
    engine.configure({'UCI_Elo': elo})
    limit = Limit(time=random.random()/10)
    return engine, elo, limit

def board_to_game(board, elo, limit):
    game = Game()
    game.headers['Event'] = 'Queen Sacrifice Search'
    game.headers['White'] = 'Stockfish'
    game.headers['Black'] = 'Stockfish'
    game.headers['Site'] = f'{elo} game with {limit.time}s time limit per move'
    game.headers['Date'] = int(time())
    switchyard = collections.deque()
    while board.move_stack:
        switchyard.append(board.pop())
    game.setup(board)
    node = game
    while switchyard:
        move = switchyard.pop()
        node = node.add_variation(move)
        board.push(move)
    game.headers['Result'] = board.result()
    return game

def translate_result(result):
    if result == '1-0':
        return 'white' 
    if result == '0-1':
        return 'black'
    return 'draw'

def find_queen_sacrifice():
    while True:
        board = Board()
        engine, elo, limit = make_engine()
        timestamp = time()
        print(f'Game {timestamp} @ {elo} / {limit.time}s per move')
        Q, q = True, True
        queen_difference_turns = 0
        first_with_no_queen = None
        all_queens_killed = False
        while not board.is_game_over():
            result = engine.play(board, limit)
            str_board = str(board)
            q = 'q' in str_board
            Q = 'Q' in str_board
            if not q and not Q:
                all_queens_killed = True
            if q ^ Q and not all_queens_killed:
                queen_difference_turns += 1
                if not first_with_no_queen:
                    first_with_no_queen = 'white' if q else 'black'
            board.push(result.move)
        winner = translate_result(board.result())
        if queen_difference_turns > 8 and winner == first_with_no_queen:
            game = board_to_game(board, elo, limit) 
            with open(f'{elo}-game-{timestamp}.pgn', 'w', encoding='utf-8') as pgn_file:
                str_game = str(game)
                print(str_game, file=pgn_file, end='\n\n')
            print('Found one!')
        engine.quit()

threads = []
for _ in range(4):
    t = Thread(target=find_queen_sacrifice)
    t.start()
    threads += [t]
for thread in threads:
    thread.join()
