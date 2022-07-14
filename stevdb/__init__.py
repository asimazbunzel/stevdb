"""Base module for database manager"""

import os
import platform
from pathlib import Path
import signal
import sys

from stevdb.base import Manager
from stevdb.io import logger, LOG_FILENAME

__version__ = "0.0.1"


def __signal_handler(signal, frame):
    """Callback for CTRL-C"""
    end()


def end():
    """Stop manager"""

    # logger.info("manager stopped")

    sys.exit(0)


def start():
    """Start manager"""

    logger.info("start database manager")

    # if only want to print database name and exit
    if core.args.log_fname:
        print(f"LOG FILENAME is: `{LOG_FILENAME}`")

    # core.show_database(name="MESArun")

    return


def main():
    """Main driver for stellar evolution manager"""

    logger.info("initialize database manager for stellar evolution models")

    # catch CTRL-C signal
    signal.signal(signal.SIGINT, __signal_handler)

    # current working directory
    curr_dir = os.getcwd()

    logger.info(f"current working directory is `{curr_dir}`")
    logger.info(
        f"{platform.python_implementation()} {platform.python_version()} detected"
    )

    # load main driver
    global core
    core = Manager()

    # start manager
    start()

    # shutdown
    end()
