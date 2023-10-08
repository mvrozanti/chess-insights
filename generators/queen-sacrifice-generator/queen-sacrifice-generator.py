#!/usr/bin/env python
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
    game.headers['White'] = game.headers['Black'] = 'Stockfish'
    game.headers['Site'] = f'{elo} game with {limit.time:.5f}s time limit per move'
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

def find_queen_sacrifice2():
    while True:
        board = Board()
        engine, elo, limit = make_engine()
        timestamp = time()
        print(f'Game {timestamp} @ {elo} / {limit.time:.5f}s per move')
        Q, q = True, True
        grace_period = 3
        should_continue = False
        check_sequence = False
        first_with_no_queen = None
        while not board.is_game_over():
            result = engine.play(board, limit)
            turn = 'white' if board.turn else 'black'
            str_board = str(board)
            q = 'q' in str_board
            Q = 'Q' in str_board
            if q ^ Q:
                is_attacking_check = board.is_check() and ((q and turn == 'white') or (Q and turn == 'black')) 
                if check_sequence and not is_attacking_check and not grace_period:
                    should_continue = True
                    break
                if not check_sequence and is_attacking_check:
                    check_sequence = True
                if not first_with_no_queen:
                    first_with_no_queen = 'white' if q else 'black'
                grace_period = max(grace_period - 1, 0)
            board.push(result.move)
        if should_continue:
            engine.quit()
            continue
        winner = translate_result(board.result())
        if check_sequence and winner == first_with_no_queen:
            game = board_to_game(board, elo, limit) 
            with open(f'{elo}-game-{timestamp}.pgn', 'w', encoding='utf-8') as pgn_file:
                print(game, file=pgn_file, end='\n\n')
            print('Found one!')
        engine.quit()

def find_queen_sacrifice():
    while True:
        board = Board()
        engine, elo, limit = make_engine()
        timestamp = time()
        print(f'Game {timestamp} @ {elo} / {limit.time:.5f}s per move')
        Q, q = True, True
        queen_difference_turns = 0
        first_with_no_queen = None
        all_queens_captured = False
        while not board.is_game_over():
            result = engine.play(board, limit)
            str_board = str(board)
            q = 'q' in str_board
            Q = 'Q' in str_board
            if not q and not Q:
                all_queens_captured = True
            if q ^ Q and not all_queens_captured:
                queen_difference_turns += 1
                if not first_with_no_queen:
                    first_with_no_queen = 'white' if q else 'black'
            board.push(result.move)
        winner = translate_result(board.result())
        if queen_difference_turns > 80 and winner == first_with_no_queen:
            game = board_to_game(board, elo, limit) 
            with open(f'{elo}-game-{timestamp}.pgn', 'w', encoding='utf-8') as pgn_file:
                str_game = str(game)
                print(str_game, file=pgn_file, end='\n\n')
            print('Found one!')
        engine.quit()

threads = []
for _ in range(4):
    t = Thread(target=find_queen_sacrifice2)
    t.start()
    threads += [t]
for thread in threads:
    thread.join()
