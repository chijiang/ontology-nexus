# backend/app/core/security.py
import bcrypt
from cryptography.fernet import Fernet
import base64
import os


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_encryption_key() -> bytes:
    """从 SECRET_KEY 派生加密密钥"""
    from app.core.config import settings
    # 使用 SECRET_KEY 的 SHA256 生成固定长度的密钥
    import hashlib
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_data(data: str) -> str:
    f = Fernet(get_encryption_key())
    return f.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted_data.encode()).decode()
