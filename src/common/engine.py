from chess.engine import SimpleEngine, Limit

from .remote_engine import make_remote, is_remote_available
from .config import config

def make_engine() -> tuple[SimpleEngine, str]:
    can_remote = is_remote_available()
    if can_remote:
        return make_remote()
    engine = SimpleEngine.popen_uci('stockfish', setpgrp=True)
    engine.configure({'Threads': 2, 'SyzygyPath': './3-4-5'})
    return engine, None

def limit() -> Limit:
    return Limit(time=config['think-time-seconds'])
