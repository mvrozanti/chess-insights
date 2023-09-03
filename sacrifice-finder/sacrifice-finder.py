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
    game.headers['Event'] = 'Sacrifice Finder'
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

def get_material_diff(str_board):
    white_count = 0
    black_count = 0
    white_count += str_board.count('P')
    black_count += str_board.count('p')
    white_count += str_board.count('N')*3
    black_count += str_board.count('n')*3
    white_count += str_board.count('B')*3
    black_count += str_board.count('b')*3
    white_count += str_board.count('R')*5
    black_count += str_board.count('r')*5
    white_count += str_board.count('Q')*9
    black_count += str_board.count('q')*9
    return white_count - black_count

def find_huge_sacrifice():
    while True:
        board = Board()
        engine, elo, limit = make_engine()
        timestamp = int(time())

        print(f'Game {timestamp} @ {elo} / {limit.time:.5f}s per move')
        biggest_diff = 0
        while not board.is_game_over():
            result = engine.play(board, limit)
            material_diff = get_material_diff(str(board))
            board.push(result.move)
            if abs(material_diff) > abs(biggest_diff):
                biggest_diff = material_diff
        winner = translate_result(board.result())
        threshold = 14
        impressive_white = winner == 'white' and biggest_diff <= -threshold
        impressive_black = winner == 'black' and biggest_diff >= threshold
        if impressive_white or impressive_black:
            game = board_to_game(board, elo, limit) 
            with open(f'{elo}-game-{timestamp}.pgn', 'w', encoding='utf-8') as pgn_file:
                str_game = str(game)
                print(str_game, file=pgn_file, end='\n\n')
            if impressive_white:
                print(f'Found an impressive white with {biggest_diff}!')
            else:
                print(f'Found an impressive black with {biggest_diff}!')
        engine.quit()

threads = []
for _ in range(5):
    t = Thread(target=find_huge_sacrifice)
    t.start()
    threads += [t]
for thread in threads:
    thread.join()
