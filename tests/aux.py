import unittest
from unittest.mock import MagicMock, patch
from src.modules.download import run

def load_games_db(mock_make_db, mock_requests_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = open('tests/testdata/testaccount_100-games.pgn').read()
    mock_requests_get.return_value = mock_response

    mock_db = MagicMock()
    mock_games = MagicMock()
    mock_games.insert_one = MagicMock()
    mock_db.games = mock_games
    mock_make_db.return_value = mock_db

    from argparse import Namespace
    args = Namespace(username='testaccount_100', months=1, limit=100)
    
    run(args)
    
    return list(map(lambda call: call._get_call_arguments()[0][0], mock_games.method_calls))