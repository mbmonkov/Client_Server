import unittest
from unittest.mock import MagicMock, patch
from app.authentication import AuthManager, is_valid_email


class TestAuthManager(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.auth = AuthManager(db_manager=self.mock_db)
        self.mock_conn = self.mock_db.get_connection.return_value
        self.mock_cursor = self.mock_conn.cursor.return_value

    def test_is_valid_email(self):
        self.assertTrue(is_valid_email("user@example.com"))
        self.assertTrue(is_valid_email("first.last@domain.org"))
        self.assertFalse(is_valid_email("invalid-email"))
        self.assertFalse(is_valid_email("user@com"))
        self.assertFalse(is_valid_email("@domain.com"))
        self.assertFalse(is_valid_email(None))

    def test_is_valid_password(self):
        self.assertTrue(self.auth.is_valid_password("ValidPass123"))
        self.assertFalse(self.auth.is_valid_password("short1A"))
        self.assertFalse(self.auth.is_valid_password("alllowercase1"))
        self.assertFalse(self.auth.is_valid_password("ALLUPPERCASE1"))
        self.assertFalse(self.auth.is_valid_password("NoDigitsPass"))
        self.assertFalse(self.auth.is_valid_password(""))

    def test_is_valid_name(self):
        self.assertTrue(self.auth.is_valid_name("Ivan"))
        self.assertFalse(self.auth.is_valid_name("ivan"))
        self.assertFalse(self.auth.is_valid_name("I"))
        self.assertFalse(self.auth.is_valid_name("Ivan1"))
        self.assertFalse(self.auth.is_valid_name("Ivan!"))

    def test_password_hashing_and_verification(self):
        password = "MySecurePassword123"
        hashed = self.auth.hash_password(password)
        self.assertNotEqual(password, hashed)
        self.assertTrue(self.auth.verify_password(hashed, password))
        self.assertFalse(self.auth.verify_password(hashed, "WrongPassword"))

    def test_register_captcha_failure(self):
        result = self.auth.register("a@b.com", "Pass123!", "Ivan", "Ivanov", "5", "10")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Failed verification!")

    def test_register_invalid_inputs(self):
        self.assertFalse(self.auth.register("bad", "Pass123!", "Ivan", "Ivanov", "1", "1")['success'])
        self.assertFalse(self.auth.register("a@b.com", "weak", "Ivan", "Ivanov", "1", "1")['success'])
        self.assertFalse(self.auth.register("a@b.com", "Pass123!", "i", "Ivanov", "1", "1")['success'])

    def test_register_success(self):
        self.mock_db.get_connection.return_value = self.mock_conn
        result = self.auth.register("test@test.com", "Admin123", "Ivan", "Ivanov", "5", "5")
        self.assertTrue(result['success'])
        self.mock_cursor.execute.assert_called()
        self.mock_conn.commit.assert_called()

    def test_register_db_error(self):
        self.mock_cursor.execute.side_effect = Exception("Duplicate entry")
        result = self.auth.register("test@test.com", "Admin123", "Ivan", "Ivanov", "5", "5")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Email is already registered!")

    def test_login_success(self):
        password = "Password123"
        hashed = self.auth.hash_password(password)
        self.mock_cursor.fetchone.return_value = (hashed, "Ivan", "Ivanov")

        result = self.auth.login("test@test.com", password, "5", "5")
        self.assertTrue(result['success'])
        self.assertEqual(result['user']['first_name'], "Ivan")

    def test_login_failure(self):
        self.mock_cursor.fetchone.return_value = None
        result = self.auth.login("nonexistent@test.com", "Password123","5", "5")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Invalid email or password!")

    def test_update_user_names_success(self):
        result = self.auth.update_user_names("test@test.com", "Newname", "Newfamily")
        self.assertTrue(result['success'])
        self.mock_conn.commit.assert_called()

    def test_update_user_names_invalid(self):
        result = self.auth.update_user_names("test@test.com", "n", "family")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Invalid name format!")

    def test_update_password_success(self):
        result = self.auth.update_password("test@test.com", "NewSecurePass1")
        self.assertTrue(result['success'])
        self.mock_conn.commit.assert_called()

    def test_update_password_weak(self):
        result = self.auth.update_password("test@test.com", "123")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "New password is too weak!")

    def test_db_connection_error_handling(self):
        self.mock_db.get_connection.return_value = None
        result = self.auth.login("a@b.com", "Pass123!", "5", "5")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Database connection error!")

    def test_logout_logic(self):
        password = "Password123"
        hashed = self.auth.hash_password(password)
        self.mock_cursor.fetchone.return_value = (hashed, "Ivan", "Ivanov")

        login_result = self.auth.login("test@test.com", password, "5", "5")
        self.assertTrue(login_result['success'])


if __name__ == '__main__':
    unittest.main()