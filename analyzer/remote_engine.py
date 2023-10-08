from threading import Lock
from chess.engine import SimpleEngine, Limit

remote_lock = Lock()

def is_remote_available():
    return not remote_lock.locked()

def set_remote_available(availability):
    if availability:
        remote_lock.release()
    else:
        remote_lock.acquire()

def make_remote():
    set_remote_available(False)
    limit = Limit(time=0.001)
    engine = SimpleEngine.popen_uci(['ssh', 'opc@oracle', 'stockfish'])
    engine.configure({'Threads': 2, 'Hash': 32})
    return engine, limit, True
