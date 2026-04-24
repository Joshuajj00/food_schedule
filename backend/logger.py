import logging
import os

# DEBUG(10)보다 낮은 커스텀 레벨 — 전체 API 페이로드·원시 응답 전용
# DEBUG와 분리해 API 키 등 민감 데이터가 기본 로그에 노출되지 않도록 함
TRACE = 5
logging.addLevelName(TRACE, 'TRACE')

def _trace(self, msg, *args, **kw):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, msg, args, **kw)

logging.Logger.trace = _trace

_LEVEL_MAP = {
    'TRACE':   TRACE,
    'DEBUG':   logging.DEBUG,
    'INFO':    logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR':   logging.ERROR,
}

_level = _LEVEL_MAP.get(os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)

logging.basicConfig(
    level=_level,
    format='%(asctime)s [%(levelname)-7s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
