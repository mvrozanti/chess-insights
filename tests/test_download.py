import unittest
from unittest.mock import MagicMock, patch
from src.modules.download import run

class TestDownload(unittest.TestCase):

    @patch('src.modules.download.make_db')
    def test_fetch_evaluation_from_db(self, mock_make_db):
        mock_db = MagicMock()
        mock_games = MagicMock()
        mock_games.insert_one = MagicMock()
        mock_db.games = mock_games
        mock_make_db.return_value = mock_db

        from argparse import Namespace
        args = Namespace(username='hikaru', months=12, limit=100)   
        
        run(args)
        
        self.assertGreater(mock_games.insert_one.call_count, 5)