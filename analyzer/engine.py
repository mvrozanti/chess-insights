from chess.engine import SimpleEngine, Limit
from remote_engine import make_remote, set_remote_available, is_remote_available

def make_engine():
    limit = Limit(time=0.001)
    if is_remote_available():
        return make_remote()
    engine = SimpleEngine.popen_uci('stockfish', setpgrp=True)
    engine.configure({'Threads': 2, 'SyzygyPath': './3-4-5'})
    return engine, limit, False
