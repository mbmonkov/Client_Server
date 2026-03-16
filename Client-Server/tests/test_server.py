import unittest
from unittest.mock import MagicMock, patch
from io import BytesIO
from server import MyHandler


class TestServerHandler(unittest.TestCase):

    def setUp(self):
        self.request = MagicMock()
        self.request.makefile.return_value = BytesIO(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.server = MagicMock()
        self.client_address = ('127.0.0.1', 12345)

    def create_handler(self):
        with patch('http.server.BaseHTTPRequestHandler.handle'):
            handler = MyHandler(self.request, self.client_address, self.server)
            handler.protocol_version = 'HTTP/1.1'
            handler.request_version = 'HTTP/1.1'
            handler.headers = {}
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = BytesIO()
            return handler

    @patch('server.SESSIONS', {})
    def test_do_get_login(self):
        handler = self.create_handler()
        handler.path = '/login'
        handler.do_GET()

        handler.send_response.assert_called_with(200)
        self.assertIn(b"Login", handler.wfile.getvalue())

    @patch('server.SESSIONS', {})
    def test_redirect_profile_unauthorized(self):
        handler = self.create_handler()
        handler.path = '/profile'
        handler.do_GET()

        handler.send_response.assert_called_with(303)
        handler.send_header.assert_any_call('Location', '/login')

    @patch('server.auth_manager')
    @patch('server.SESSIONS', {})
    def test_do_post_login_success(self, mock_auth):
        mock_auth.login.return_value = {'success': True, 'user': {'email': 'test@test.com'}}

        handler = self.create_handler()
        post_data = b"email=test@test.com&password=pass123&captcha_answer=10"
        handler.rfile = BytesIO(post_data)
        handler.headers = {'Content-Length': str(len(post_data))}
        handler.path = '/login_action'

        handler.do_POST()

        handler.send_header.assert_any_call('Location', '/profile')

    @patch('server.SESSIONS', {'test-sid': {'user': {'email': 'test@test.com'}}})
    def test_do_get_logout(self):
        handler = self.create_handler()
        handler.get_session_id = MagicMock(return_value='test-sid')
        handler.path = '/logout'

        from server import SESSIONS
        handler.do_GET()

        self.assertNotIn('test-sid', SESSIONS)
        handler.send_response.assert_called_with(303)
        handler.send_header.assert_any_call('Location', '/login')

    @patch('server.auth_manager')
    @patch('server.SESSIONS', {'test-sid': {'user': {'email': 'test@test.com'}}})
    def test_do_post_update_profile_success(self, mock_auth):
        mock_auth.update_user_names.return_value = {'success': True}

        handler = self.create_handler()
        handler.get_session_id = MagicMock(return_value='test-sid')

        post_data = b"first_name=NewName&last_name=NewFamily"
        handler.rfile = BytesIO(post_data)
        handler.headers = {'Content-Length': str(len(post_data))}
        handler.path = '/update_profile'

        handler.do_POST()

        from server import SESSIONS
        self.assertEqual(SESSIONS['test-sid']['user']['first_name'], 'NewName')
        handler.send_header.assert_any_call('Location', '/profile?updated=1')


if __name__ == '__main__':
    unittest.main()