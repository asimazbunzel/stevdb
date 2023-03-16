# type: ignore[attr-defined]
import os
import platform
import pprint
import signal
import sys
import time

from stevdb import version
from stevdb.base import Manager
from stevdb.io import LOG_FILENAME, logger


def __signal_handler(signal, frame):
    """Callback for CTRL-C"""

    end()


def end() -> None:
    """Stop manager"""

    # time it
    end = time.time()

    logger.info(f"[-- manager uptime: {end - start:.2f} sec --]")
    logger.info("manager stopped")

    sys.exit(0)


def start() -> None:
    """Start manager"""

    # time it
    global start
    start = time.time()

    # if only want to print database name and exit
    if core.args.log_fname:
        print(f"LOG FILENAME is: `{LOG_FILENAME}`")
        end()

    # show config and exit
    if core.args.show_config:
        pprint.pprint(core.config)
        end()

    # useful shortcuts
    admin_dict = core.config.get("Admin")
    mesa_dict = core.config.get("MESA")
    stevdb_dict = core.config.get("Stevdb")

    # set up the grid manager
    if mesa_dict.get("id") == "mesabinary":
        global gridManager
        gridManager = MESAbinaryGrid(
            replace_evolutions=admin_dict.get("replace_evolutions"),
            database_name=admin_dict.get("database_name"),
            overwrite_database=admin_dict.get("overwrite_database"),
            template_directory=mesa_dict.get("template_directory"),
            runs_directory=mesa_dict.get("runs_directory"),
            mesa_binary_dict=mesa_dict.get("mesabinary"),
            stevdb_dict=stevdb_dict,
        )
    elif core.config.get("Admin")["id"] == "mesastar":
        logger.critical("`mesastar` grid is not ready to be used")
        sys.exit(1)
    else:
        logger.critical(f"unknown id: {core.config.get('Admin')['id']}")
        sys.exit(1)


def main() -> None:
    """Main driver for stellar evolution manager"""

    logger.info("********************************************************")
    logger.info("          Stellar Evolution Database Manager            ")
    logger.info("********************************************************")
    logger.info("initialize database manager for stellar evolution models")

    curr_dir: str = os.getcwd()
    logger.info(f"current working directory is `{curr_dir}`")
    logger.info(f"{platform.python_implementation()} {platform.python_version()} detected")

    # catch CTRL-C signal
    signal.signal(signal.SIGINT, __signal_handler)

    # load main driver
    global core
    core = Manager()

    # start manager
    start()

    # start loop
    # watch()


if __name__ == "__main__":
    main()
