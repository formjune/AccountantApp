import logging
import re
from sql import EngineSQL


class IncorrectInput(Exception):
    """in case of incorrect dialog input"""


class DialogLock(object):

    locked: bool = False


def connection(run):
    """method connects to database"""
    def wrapped(*args, **kwargs):
        EngineSQL.checkConnection()
        EngineSQL.s = EngineSQL.Session()
        try:
            return run(*args, **kwargs)
        except IncorrectInput:
            return
        except:
            logging.exception("exception:")
    return wrapped


def connectionWithLock(run):
    def wrapped(*args, **kwargs):
        if DialogLock.locked:
            return
        EngineSQL.checkConnection()
        EngineSQL.s = EngineSQL.Session()
        try:
            DialogLock.locked = True
            return run(*args, **kwargs)
        except IncorrectInput:
            return
        except:
            logging.exception("exception:")
        finally:
            DialogLock.locked = False
    return wrapped


def unsafe(run):
    def wrapped(*args, **kwargs):
        try:
            return run(*args, **kwargs)
        except IncorrectInput:
            return
        except:
            logging.exception("exception:")
    return wrapped



def extractTxHash(tx_str: str) -> str | None:
    """
    Пытаемся найти в тексте что-то вида:
      0x + 64 шестнадцатеричных символов
    Возвращаем строку (в нижнем регистре) или None, если ничего похожего не нашли.
    """
    if not tx_str:
        return None
    
    # Регулярка: ищем 0x, за которым ровно 64 символа [0-9a-fA-F]
    match = re.search(r'(0x[0-9a-fA-F]{64})', tx_str)
    if match:
        return match.group(1).lower()
    return None