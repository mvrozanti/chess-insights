from chess.engine import SimpleEngine, Limit

from .remote_engine import make_remote, is_remote_available
from .config import config

def make_engine(remote: bool = None) -> tuple[SimpleEngine, bool]:
    if remote and is_remote_available():
        return make_remote(remote)
    engine = SimpleEngine.popen_uci('stockfish', setpgrp=True)
    engine.configure({'Threads': 2, 'SyzygyPath': './3-4-5'})
    return engine, False

def limit() -> Limit:
    return Limit(time=config['think-time-seconds'])
