from chess.engine import SimpleEngine, Limit

def make_engine():
    elo = 2850
    engine = SimpleEngine.popen_uci('stockfish')
    engine.configure({'UCI_LimitStrength': True})
    engine.configure({'UCI_Elo': elo})
    engine.configure({'Threads': 4})
    limit = Limit(time=0.001)
    return engine, elo, limit