"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mstevdb` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``stevdb.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``stevdb.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import os
from pathlib import Path
import platform
import signal
import sys

from .base import Manager
from .io.logger import LOG_FILENAME, logger
from .mesabinary_runs import MESAbinaryGrid


def __signal_handler(signal, frame):
    """Callback for CTRL-C"""

    end()


def end():
    """Stop manager"""

    logger.info("manager stopped")

    sys.exit(0)


def loop():
    """Manager will be updated in this loop"""

    # first thing, make a summary of each simulation
    gridManager.create_summary()

    # keep on going with manager being active
    keep_alive = True
    while keep_alive:
        pass


def start():
    """Start manager"""

    # if only want to print database name and exit
    if core.args.log_fname:
        print(f"LOG FILENAME is: `{LOG_FILENAME}`")
        sys.exit(0)

    # show config and exit
    if core.args.show_config:
        print(core.config)
        sys.exit(0)

    # set up the grid manager
    config_dict = core.config.get("Admin")
    if core.config.get("Admin")["id"] == "mesabinary":
        global gridManager
        gridManager = MESAbinaryGrid(
                replace_evolutions=config_dict.get("replace_evolutions"),
                database_name=config_dict.get("database_name"),
                overwrite_database=config_dict.get("overwrite_database"),
                mesa_binary_dict=config_dict.get("mesabinary"),
                mesa_config_dict=core.config.get("MESA"),
        )
    elif core.config.get("Admin")["id"] == "mesastar":
        logger.error("`mesastar` grid is not ready to be used")
        sys.exit(1)
    else:
        logger.error(f"unknown id: {core.config.get('Admin')['id']}")
        sys.exit(1)


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

    # # load main driver
    global core
    core = Manager()

    # start manager
    start()

    # start loop
    loop()

    # shutdown
    end()
