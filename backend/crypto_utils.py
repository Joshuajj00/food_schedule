"""
API 키 암호화/복호화 유틸리티
- cryptography 라이브러리의 Fernet(대칭키) 사용
- 우선순위: 환경변수 ENCRYPTION_KEY → ENCRYPTION_KEY_PATH 파일 → 기본 경로
- 기본 경로는 데이터 DB와 분리된 위치 사용 (보안)
"""
import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet

# 키 파일 위치 결정 우선순위:
# 1. 환경변수 ENCRYPTION_KEY (직접 키값)
# 2. 환경변수 ENCRYPTION_KEY_PATH (키파일 경로)
# 3. ~/.config/diet_assistant/encryption.key (DB와 분리된 기본 위치)

_DEFAULT_KEY_DIR = Path.home() / '.config' / 'diet_assistant'
_DEFAULT_KEY_FILE = _DEFAULT_KEY_DIR / 'encryption.key'


def _get_or_create_key() -> bytes:
    env_key = os.getenv('ENCRYPTION_KEY', '').strip()
    if env_key:
        # 44자 base64 키이거나, 32자 미만 패스워드는 패딩 후 변환
        if len(env_key) == 44:
            return env_key.encode()
        return base64.urlsafe_b64encode(env_key.encode().ljust(32)[:32])

    key_path_env = os.getenv('ENCRYPTION_KEY_PATH', '').strip()

    if key_path_env:
        key_file = Path(key_path_env)
        if key_file.exists():
            return key_file.read_bytes()
        # 명시적 경로가 지정됐는데 파일 없음 → 자동 생성 금지 (read-only 마운트 대응)
        raise RuntimeError(
            f"ENCRYPTION_KEY_PATH='{key_path_env}' 파일이 존재하지 않습니다.\n"
            f"컨테이너 시작 전 호스트에서 키를 생성하세요:\n"
            f"  mkdir -p secrets\n"
            f"  python3 -c \"from cryptography.fernet import Fernet; "
            f"open('secrets/encryption.key', 'wb').write(Fernet.generate_key())\"\n"
            f"  chmod 600 secrets/encryption.key"
        )

    # 기본 경로: 자동 생성 허용
    key_file = _DEFAULT_KEY_FILE
    if key_file.exists():
        return key_file.read_bytes()

    key = Fernet.generate_key()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(key)
    try:
        os.chmod(key_file, 0o600)
    except (OSError, NotImplementedError):
        pass
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
