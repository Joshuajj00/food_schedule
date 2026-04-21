import logging
import os

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
