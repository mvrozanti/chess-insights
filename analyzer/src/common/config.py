import appdirs
from os import path as op
import json
import os

DATA_DIR = appdirs.user_data_dir(appname='chess-playground')
DEFAULT_CONFIG = {
    "downloader-user-agent-username": "anonymous"
}

if not op.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def get_config_file_path():
    return op.join(DATA_DIR, 'config.json')

def read_config():
    config_file_path = get_config_file_path()
    if op.exists(config_file_path):
        return json.load(open(config_file_path))
    else:
        write_default_config()
        return read_config()

def write_default_config():
    json.dump(DEFAULT_CONFIG, open(get_config_file_path(), 'w'))

config = read_config()