import unittest
from unittest.mock import MagicMock, patch
from database import DatabaseManager
from mysql.connector import Error


class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseManager()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

    @patch('mysql.connector.connect')
    def test_get_connection_success(self, mock_connect):
        mock_connect.return_value = self.mock_conn
        conn = self.db.get_connection()

        self.assertIsNotNone(conn)
        mock_connect.assert_called_with(**self.db.config)

    @patch('mysql.connector.connect')
    def test_get_connection_failure(self, mock_connect):
        mock_connect.side_effect = Error("Access denied")
        conn = self.db.get_connection()

        self.assertIsNone(conn)

    @patch('database.DatabaseManager.get_connection')
    def test_execute_success(self, mock_get_conn):
        mock_get_conn.return_value = self.mock_conn

        query = "INSERT INTO users (email) VALUES (%s)"
        params = ("test@example.com",)

        result = self.db.execute(query, params)

        self.assertTrue(result)
        self.mock_cursor.execute.assert_called_with(query, params)
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

    @patch('database.DatabaseManager.get_connection')
    def test_fetch_one_success(self, mock_get_conn):
        mock_get_conn.return_value = self.mock_conn
        expected_row = (1, "test@test.com", "John")
        self.mock_cursor.fetchone.return_value = expected_row

        query = "SELECT * FROM users WHERE id = %s"
        result = self.db.fetch_one(query, (1,))

        self.assertEqual(result, expected_row)
        self.mock_cursor.execute.assert_called_once()

    @patch('mysql.connector.connect')
    def test_setup_db_logic(self, mock_connect):
        mock_temp_conn = MagicMock()
        mock_connect.side_effect = [mock_temp_conn, self.mock_conn]

        self.db.setup_db()

        self.assertTrue(mock_temp_conn.cursor.called)
        self.mock_conn.commit.assert_called()


if __name__ == '__main__':
    unittest.main()