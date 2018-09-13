"""
utils.py : common utility functions used throughout the program. Includes path
           splitting and checking using the os library, a custom curses border
           drawer, and variable formatting.
"""
__author__ = "Samuel Whang"

from typing import Union, Tuple
import curses
import logging
import datetime
import os

def setup_logger(name, logfile, level=logging.INFO, logformat=None):
    """Handles creation of multiple loggers"""
    if logformat is None:
        logformat = "%(asctime)s %(classname)s: %(message)s"

    formatter = logging.Formatter(logformat, "%H:%M:%S")

    with open(logfile, 'w'):
        pass

    handler = logging.FileHandler(logfile)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

def log_message(logger, message, extra=None):
    logger.info(message, extra)

def format_directory_path(path: str) -> str:
    """
    Replaces windows style path seperators to forward-slashes and adds another
    slash to the end of the string
    """
    formatted_path = path.replace('\\', '/')
    if formatted_path[-1] is not '/':
        formatted_path += '/'
    return formatted_path

def check_directory_path(path: str) -> bool:
    return os.path.isdir(path)

def filename_and_extension(path: str) -> Tuple[str, str]:
    return os.path.splitext(path)

def border(screen: object, x: int, y: int, dx: int, dy: int) -> None:
    """
    Draws a box with the given input parameters using the default characters
    """
    screen.vline(y, x, curses.ACS_SBSB, dy)
    screen.vline(y, x + dx, curses.ACS_SBSB, dy)
    screen.hline(y, x, curses.ACS_BSBS, dx)
    screen.hline(y + dy, x, curses.ACS_BSBS, dx)
    screen.addch(y, x, curses.ACS_BSSB)
    screen.addch(y, x + dx, curses.ACS_BBSS)
    screen.addch(y + dy, x, curses.ACS_SSBB)
    screen.addch(y + dy, x + dx, curses.ACS_SBBS)

def format_float(number: Union[int, float]) -> float:
    return f"{number:.2f}"

def format_date(date) -> str:
    return datetime.date(date[0], date[1], date[2]).isoformat()
