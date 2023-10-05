from chess.engine import SimpleEngine, Limit

def make_engine():
    limit = Limit(time=0.001)
    engine = SimpleEngine.popen_uci('stockfish')
    instance = engine
    engine.configure({'Threads': 2, 'Hash': 2**7})
    return engine, limit