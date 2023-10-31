from threading import Lock
from chess.engine import SimpleEngine

remote_lock = Lock()

def is_remote_available() -> bool:
    return not remote_lock.locked()

def set_remote_available(availability: bool) -> None:
    if availability:
        remote_lock.release()
    else:
        remote_lock.acquire()

def make_remote(remote: bool) -> tuple[SimpleEngine, bool]:
    set_remote_available(False)
    engine = SimpleEngine.popen_uci(['ssh', remote, 'stockfish'])
    engine.configure({'Threads': 2, 'Hash': 32})
    return engine, True
