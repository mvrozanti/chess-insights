from chess.engine import SimpleEngine, Limit
from .remote_engine import make_remote, is_remote_available

def make_engine():
    if is_remote_available():
        return make_remote()
    engine = SimpleEngine.popen_uci('stockfish', setpgrp=True)
    engine.configure({'Threads': 2, 'SyzygyPath': './3-4-5'})
    return engine, False

def limit():
    return Limit(time=0.001)