import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "dayz_discord_ops_repo/src"))

from dayz_discord_ops.casino import BlackjackView
import dayz_discord_ops.database

class TestCasino(unittest.IsolatedAsyncioTestCase):
    async def test_blackjack_mechanics(self):
        # Mock bot/user
        bot = MagicMock()
        user = MagicMock()
        
        # Test Deck
        view = BlackjackView(bot, user, 100)
        self.assertEqual(len(view.deck), 52 - 4) # 4 cards dealt
        
        # Test Score
        self.assertEqual(view.score([10, 10]), 20)
        self.assertEqual(view.score([10, 11]), 21) # Ace handling
        self.assertEqual(view.score([10, 10, 10]), 30)
        self.assertEqual(view.score([10, 11, 10]), 21) # Ace becomes 1

class TestDatabaseSchema(unittest.TestCase):
    def test_schema_sql(self):
        # We just want to ensure the SQL strings are valid syntax (roughly)
        # and methods exist
        db = dayz_discord_ops.database.Database(MagicMock())
        # Inspect init_schema code by reflection or just ensure methods exist
        self.assertTrue(hasattr(db, 'create_ticket'))
        self.assertTrue(hasattr(db, 'close_ticket'))

class TestFileGeneration(unittest.TestCase):
    def test_custom_spawns(self):
        path = "dayzxb_missions/dayzOffline.chernarusplus/custom/custom_spawns.c"
        self.assertTrue(os.path.exists(path), "custom_spawns.c should exist")
        with open(path, 'r') as f:
            content = f.read()
            self.assertIn("void SpawnCustomObjects()", content)
            self.assertIn("CreateObject", content)
            
    def test_init_c_include(self):
        path = "dayzxb_missions/dayzOffline.chernarusplus/init.c"
        with open(path, 'r') as f:
            content = f.read()
            self.assertIn('#include "$mission:custom/custom_spawns.c"', content)
            self.assertIn("SpawnCustomObjects();", content)

if __name__ == '__main__':
    unittest.main()
