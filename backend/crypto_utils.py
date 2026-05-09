"""
API 키 암호화/복호화 유틸리티
- cryptography 라이브러리의 Fernet(대칭키) 사용
- 암호화 키는 환경변수 ENCRYPTION_KEY 또는 자동 생성된 키 파일에서 로드
"""
import os
import base64
from cryptography.fernet import Fernet

_KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '.encryption_key')


def _get_or_create_key() -> bytes:
    """환경변수 또는 키 파일에서 암호화 키를 로드. 없으면 생성."""
    env_key = os.getenv('ENCRYPTION_KEY', '')
    if env_key:
        return env_key.encode() if len(env_key) == 44 else base64.urlsafe_b64encode(env_key.encode().ljust(32)[:32])

    if os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, 'rb') as f:
            return f.read()

    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(_KEY_FILE), exist_ok=True)
    with open(_KEY_FILE, 'wb') as f:
        f.write(key)
    os.chmod(_KEY_FILE, 0o600)
    return key


_fernet = Fernet(_get_or_create_key())


def encrypt(plaintext: str) -> str:
    """평문 문자열을 암호화하여 base64 문자열로 반환"""
    if not plaintext:
        return ''
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """암호화된 base64 문자열을 복호화하여 평문 반환"""
    if not ciphertext:
        return ''
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        import logging
        logging.getLogger('backend.crypto_utils').warning(
            "API 키 복호화 실패 — 암호화 키 불일치 또는 데이터 손상. 빈 문자열 반환."
        )
        return ''
