#!/usr/bin/env python
from chess import WHITE, BLACK
from chess.engine import SimpleEngine, Limit
from chess.pgn import read_game
from collections import OrderedDict

def make_engine():
    elo = 2850
    engine = SimpleEngine.popen_uci('stockfish')
    engine.configure({'UCI_LimitStrength': True})
    engine.configure({'UCI_Elo': elo})
    engine.configure({'Threads': 4})
    limit = Limit(time=0.001)
    return engine, elo, limit

def get_game_accuracy():
    engine, _, limit = make_engine()
    with open('vegan_cheemsburger9000_vs_vikkistar007_2023.09.02.pgn', "r") as pgn_file:
        game = read_game(pgn_file)
    headers = game.headers
    print("Event:", headers.get("Event"))
    print("White:", headers.get("White"))
    print("Black:", headers.get("Black"))

    board = game.board()
    move_accuracy_white = []
    move_accuracy_black = []
    for actual_move_idx, actual_move in enumerate(game.mainline_moves()):
        san_move = board.san(actual_move)
        print("Evaluating {} {} ({:d} of {}): ".format("white's" if board.turn else "black's", san_move, actual_move_idx, len(list(game.mainline_moves()))), end="", flush=True)
        moves = {}
        for legal_move in board.legal_moves:
            info = engine.analyse(board, limit, root_moves=[legal_move])
            try:
                value = info['score'].relative.cp
            except:
                value = 10000 - info['score'].relative.mate()
                if info['score'].relative.mate() < 0:
                    value = -value
            if value not in moves:
                moves[value] = []
            moves[value].append(legal_move)
        ranked_moves = OrderedDict(sorted(moves.items(), key=lambda x: x[0], reverse=True))
        legal_move_count = len(ranked_moves)
        actual_move_rank = None
        for idx, moves in enumerate(ranked_moves.values()):
            if actual_move in moves:
                actual_move_rank = idx
                break
        raw_move_accuracy = (legal_move_count - actual_move_rank)/legal_move_count
        if board.turn == WHITE:
            move_accuracy_white.append(raw_move_accuracy)
        if board.turn == BLACK:
            move_accuracy_black.append(raw_move_accuracy)
        board.push(actual_move)
        print(raw_move_accuracy)
    engine.quit()
    return move_accuracy_white, move_accuracy_black

move_accuracy_white, move_accuracy_black = get_game_accuracy()

white_accuracy = sum(move_accuracy_white) / len(move_accuracy_white)
black_accuracy = sum(move_accuracy_black) / len(move_accuracy_black)

print(white_accuracy)
print(black_accuracy)
