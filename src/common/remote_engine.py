from threading import Lock
from chess.engine import SimpleEngine

remote_lock = {}
REMOTES = []

def add_remotes(remotes: list[str]):
    for remote in remotes:
        remote_lock[remote] = Lock()

def get_remote_available() -> bool:
    for remote, lock in remote_lock.items():
       if not lock.locked():
           return remote

def is_remote_available() -> bool:
    return bool(get_remote_available())

def set_remote_available(remote: str, availability: bool) -> None:
    if availability:
        remote_lock[remote].release()
    else:
        remote_lock[remote].acquire()

def make_remote() -> tuple[SimpleEngine, bool]:
    remote = get_remote_available()
    set_remote_available(remote, False)
    engine = SimpleEngine.popen_uci(['ssh', remote, 'stockfish'])
    engine.configure({'Threads': 2, 'Hash': 32})
    return engine, remote
