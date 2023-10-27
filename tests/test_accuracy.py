import sys
import unittest
from unittest.mock import patch, MagicMock

from src.modules.accuracy import run
from .aux import load_games_db

class TestAccuracy(unittest.TestCase):

    @patch('src.modules.accuracy.make_db')
    @patch('src.modules.accuracy.count_user_games')
    @patch('src.modules.download.requests.get')
    @patch('src.modules.download.make_db')
    def test_accuracy(self, mock_make_db, mock_requests_get, mock_count_user_games, mock_accuracy_make_db):
        documents = load_games_db(mock_make_db, mock_requests_get)
        
        mock_db = MagicMock()
        mock_games = MagicMock()
        mock_games.find_one = MagicMock()
        mock_games.find_one.return_value = documents[0]
        mock_count_user_games.return_value = 1
        mock_db.games = mock_games
        mock_make_db.return_value = mock_db
        mock_accuracy_make_db.return_value = mock_db

        
        from argparse import Namespace
        args = Namespace(username='testaccount_100', worker_count=2, color='any', limit=sys.maxsize)
        
        run(args)
