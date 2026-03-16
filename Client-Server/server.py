import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
import uuid
import re
from app.authentication import AuthManager
from app.captcha import MathCaptcha
from database import DatabaseManager

db_manager = DatabaseManager()
auth_manager = AuthManager(db_manager)
captcha_tool = MathCaptcha()

SESSIONS = {}


class MyHandler(BaseHTTPRequestHandler):

    def get_session_id(self):
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookie = SimpleCookie(cookie_header)
            if 'session_id' in cookie:
                return cookie['session_id'].value
        return None

    def get_post_data(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        parsed = urllib.parse.parse_qs(post_data)
        return {k: v[0] for k, v in parsed.items()}

    def redirect(self, location, set_cookie=None):
        self.send_response(303)
        self.send_header('Location', location)
        if set_cookie:
            self.send_header('Set-Cookie', f'session_id={set_cookie}; HttpOnly; Path=/')
        self.end_headers()

    def render(self, template_name, context=None):
        if context is None:
            context = {}
        if 'error' not in context:
            context['error'] = ''
        if 'msg' not in context:
            context['msg'] = ''

        try:
            with open(f"templates/{template_name}", "r", encoding="utf-8") as f:
                content = f.read()
                for key, value in context.items():
                    content = content.replace(f"{{{{{key}}}}}", str(value))

                content = re.sub(r"\{\{.*?\}\}", "", content)

                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "Template Not Found")

    def do_GET(self):
        sid = self.get_session_id()
        parsed_url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_url.query)
        path = parsed_url.path

        if path == '/' or path == '/login':
            question, answer = captcha_tool.generate_challenge()

            temp_sid = sid if sid else str(uuid.uuid4())
            if temp_sid not in SESSIONS:
                SESSIONS[temp_sid] = {}
            SESSIONS[temp_sid]['login_captcha'] = answer

            msg = ""
            if 'success' in params:
                msg = "Registration successful! You can now log in."

            error = ""
            if 'error' in params:
                error = "Invalid email or password!"
            elif 'captcha_error' in params:
                error = "Failed verification!"

            if not sid:
                self.send_response(200)
                self.send_header('Set-Cookie', f'session_id={temp_sid}; HttpOnly; Path=/')
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()

            self.render('login.html', {
                'msg': msg,
                'error': error,
                'captcha_question': question,
                'captcha_secret': answer
            })

        elif path == '/register':
            question, answer = captcha_tool.generate_challenge()

            temp_sid = sid if sid else str(uuid.uuid4())
            if temp_sid not in SESSIONS:
                SESSIONS[temp_sid] = {}
            SESSIONS[temp_sid]['captcha'] = answer

            error_msg = params.get('error', [''])[0]

            self.send_response(200)
            if not sid:
                self.send_header('Set-Cookie', f'session_id={temp_sid}; HttpOnly; Path=/')
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            with open("templates/register.html", "r", encoding="utf-8") as f:
                content = f.read()
                content = content.replace("{{captcha_question}}", question)
                content = content.replace("{{error}}", error_msg)
                self.wfile.write(content.encode('utf-8'))

        elif path == '/profile':
            if sid in SESSIONS and 'user' in SESSIONS[sid]:
                user = SESSIONS[sid]['user']
                msg = "Profile updated successfully!" if 'updated' in params else ""
                error_msg = params.get('error', [''])[0]
                self.render('profile.html', {
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'email': user['email'],
                    'msg': msg,
                    'error': error_msg
                })
            else:
                self.redirect('/login')

        elif path == '/logout':
            if sid in SESSIONS:
                del SESSIONS[sid]
            self.redirect('/login')

    def do_POST(self):
        sid = self.get_session_id()
        data = self.get_post_data()

        if self.path == '/register_action':
            saved_captcha = SESSIONS.get(sid, {}).get('captcha') if sid else None
            result = auth_manager.register(
                email=data.get('email'),
                password=data.get('password'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                captcha_user=data.get('captcha_answer'),
                captcha_secret=saved_captcha
            )
            if result['success']:
                self.redirect('/login?success=1')
            else:
                error_encoded = urllib.parse.quote(result['error'])
                self.redirect(f'/register?error={error_encoded}')

        elif self.path == '/login_action':
            saved_captcha = SESSIONS.get(sid, {}).get('login_captcha') if sid else None

            result = auth_manager.login(
                email=data.get('email'),
                password=data.get('password'),
                captcha_user=data.get('captcha_answer'),
                captcha_secret=saved_captcha
            )

            if result['success']:
                new_sid = str(uuid.uuid4())
                SESSIONS[new_sid] = {'user': result['user']}
                if sid in SESSIONS:
                    del SESSIONS[sid]
                self.redirect('/profile', set_cookie=new_sid)
            else:
                if result.get('error') == "Failed verification!":
                    self.redirect('/login?captcha_error=1')
                else:
                    self.redirect('/login?error=1')

        elif self.path == '/update_profile':
            if sid in SESSIONS and 'user' in SESSIONS[sid]:
                user_email = SESSIONS[sid]['user']['email']
                result = auth_manager.update_user_names(
                    email=user_email,
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name')
                )

                if result['success']:
                    SESSIONS[sid]['user']['first_name'] = data.get('first_name')
                    SESSIONS[sid]['user']['last_name'] = data.get('last_name')
                    self.redirect('/profile?updated=1')
                else:
                    error_encoded = urllib.parse.quote(result['error'])
                    self.redirect(f'/profile?error={error_encoded}')
            else:
                self.redirect('/login')

        elif self.path == '/update_password':
            if sid in SESSIONS and 'user' in SESSIONS[sid]:
                user_email = SESSIONS[sid]['user']['email']
                result = auth_manager.update_password(
                    email=user_email,
                    new_password=data.get('new_password')
                )

                if result['success']:
                    self.redirect('/profile?updated=1')
                else:
                    error_encoded = urllib.parse.quote(result['error'])
                    self.redirect(f'/profile?error={error_encoded}')
            else:
                self.redirect('/login')

if __name__ == '__main__':
    db_manager.setup_db()
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, MyHandler)
    print("Server started at http://localhost:8000")
    httpd.serve_forever()