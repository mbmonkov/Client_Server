import hashlib
import os
import re
from typing import Any, Dict, Optional, Union

def is_valid_email(email: Optional[str]) -> bool:
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(regex, email)) if email else False

class AuthManager:
    def __init__(self, db_manager: Any = None) -> None:
        self.db = db_manager

    def is_valid_password(self, password: str) -> bool:
        if not password or len(password) < 8:
            return False
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        return has_upper and has_lower and has_digit

    def is_valid_name(self, name: str) -> bool:
        if not name or len(name) < 2:
            return False
        if not name.isalpha():
            return False
        return name[0].isupper()

    def hash_password(self, password: str) -> bytes:
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt + pwd_hash

    def verify_password(self, stored_data: bytes, provided_password: str) -> bool:
        salt = stored_data[:16]
        stored_hash = stored_data[16:]
        new_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt, 100000)
        return new_hash == stored_hash

    def register(self, email: str, password: str, first_name: str, last_name: str, captcha_user: str, captcha_secret: str) -> Dict[str, Any]:
        if not captcha_user or captcha_user.strip() != captcha_secret.strip():
            return {"success": False, "error": "Failed verification!"}

        if not is_valid_email(email):
            return {"success": False, "error": "Invalid email format!"}
        if not self.is_valid_password(password):
            return {"success": False, "error": "Password is too weak!"}
        if not (self.is_valid_name(first_name) and self.is_valid_name(last_name)):
            return {"success": False, "error": "Invalid names! Use only letters and start with uppercase."}

        hashed = self.hash_password(password)
        conn = self.db.get_connection()
        if not conn:
            return {"success": False, "error": "Database connection error!"}

        try:
            cursor = conn.cursor()
            query = "INSERT INTO users (email, password, first_name, last_name) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (email, hashed, first_name, last_name))
            conn.commit()
            return {"success": True}
        except Exception:
            return {"success": False, "error": "Email is already registered!"}
        finally:
            conn.close()

    def login(self, email: str, password: str, captcha_user: str, captcha_secret: str) -> Dict[str, Any]:
        if not captcha_user or captcha_user.strip() != captcha_secret.strip():
            return {"success": False, "error": "Failed verification!"}

        conn = self.db.get_connection()
        if not conn:
            return {"success": False, "error": "Database connection error!"}

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password, first_name, last_name FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user and self.verify_password(user[0], password):
                return {"success": True, "user": {"email": email, "first_name": user[1], "last_name": user[2]}}

            return {"success": False, "error": "Invalid email or password!"}
        finally:
            conn.close()

    def update_user_names(self, email: str, first_name: str, last_name: str) -> Dict[str, Any]:
        if not (self.is_valid_name(first_name) and self.is_valid_name(last_name)):
            return {"success": False, "error": "Invalid name format!"}

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            query = "UPDATE users SET first_name = %s, last_name = %s WHERE email = %s"
            cursor.execute(query, (first_name, last_name, email))
            conn.commit()
            return {"success": True}
        except Exception:
            return {"success": False, "error": "Failed to update names."}
        finally:
            conn.close()

    def update_password(self, email: str, new_password: str) -> Dict[str, Any]:
        if not self.is_valid_password(new_password):
            return {"success": False, "error": "New password is too weak!"}

        hashed = self.hash_password(new_password)
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            query = "UPDATE users SET password = %s WHERE email = %s"
            cursor.execute(query, (hashed, email))
            conn.commit()
            return {"success": True}
        except Exception:
            return {"success": False, "error": "Failed to update password."}
        finally:
            conn.close()