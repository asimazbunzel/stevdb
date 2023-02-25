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
import platform
import signal
import sys
import time

from .base import Manager
from .io.logger import LOG_FILENAME
from .io.logger import logger
from .mesa import NoMESArun
from .mesabinary_runs import MESAbinaryGrid


def __signal_handler(signal, frame):
    """Callback for CTRL-C"""

    end()


def end():
    """Stop manager"""

    # time it
    end = time.time()

    logger.info(f"[-- manager uptime: {end - start:.2f} sec --]")
    logger.info("manager stopped")

    sys.exit(0)


def watch():
    """Manager will be updated in this loop"""

    # useful shortcuts
    admin_dict = core.config.get("Admin")

    # first thing, make a summary of each simulation
    gridManager.do_run_summary()

    # keep on going with manager being active
    keep_alive = True
    while keep_alive:

        # get the previous list of runs
        previous_list_of_runs = gridManager.runs

        # wait a while before updating list of runs
        logger.info(f"manager will now enter into waiting mode for {admin_dict.get('waiting_time_in_sec')} sec")
        time.sleep(admin_dict.get("waiting_time_in_sec"))

        # update list of runs and compare to previous one
        gridManager.update_list_of_models()
        new_list_of_runs = gridManager.runs

        if len(new_list_of_runs) > len(previous_list_of_runs):
            logger.info(f"new {len(new_list_of_runs) - len(previous_list_of_runs)} run(s) found ! trying to update database")
            # find which elements are new
            previous_set = set(previous_list_of_runs)
            new_set = set(new_list_of_runs)
            unique_runs = new_set.difference(previous_set)
            logger.info(f"new runs to include into database: {str(unique_runs)}")

            # loop through new runs to append to database using single methods of the MESAbinaryGrid class
            for run in unique_runs:

                # remove absolute path, get folder name where run is located
                name = run.split("/")[-2]

                # create summary
                try:
                    NewSummary = gridManager.run1_summary(run_name=name)

                except (NoMESArun, NotImplementedError):
                    continue

                # if no exception was triggered, insert data into it
                else:
                    gridManager.do_summary_info(runSummary=NewSummary)

        elif len(new_list_of_runs) < len(previous_list_of_runs):
            logger.error("new list of runs is less than earlier. something is VERY WRONG")
            keep_alive = False

        else:
            logger.info("no new runs found ! continue waiting")

    end()


def start():
    """Start manager"""

    # time it
    global start
    start = time.time()

    # if only want to print database name and exit
    if core.args.log_fname:
        print(f"LOG FILENAME is: `{LOG_FILENAME}`")
        sys.exit(0)

    # show config and exit
    if core.args.show_config:
        print(core.config)
        sys.exit(0)

    # useful shortcuts
    admin_dict = core.config.get("Admin")
    mesa_dict = core.config.get("MESA")
    stevdb_dict = core.config.get("Stevdb")

    # set up the grid manager
    if mesa_dict.get("id") == "mesabinary":
        global gridManager
        gridManager = MESAbinaryGrid(
            replace_evolutions=admin_dict.get("replace_evolutions"),
            database_name=stevdb_dict.get("database_name"),
            drop_tables=stevdb_dict.get("drop_tables"),
            template_directory=mesa_dict.get("template_directory"),
            runs_directory=mesa_dict.get("runs_directory"),
            mesa_binary_dict=mesa_dict.get("mesabinary"),
            stevdb_dict=stevdb_dict,
        )
    elif core.config.get("Admin")["id"] == "mesastar":
        logger.error("`mesastar` grid is not ready to be used")
        sys.exit(1)
    else:
        logger.error(f"unknown id: {core.config.get('Admin')['id']}")
        sys.exit(1)


def main():
    """Main driver for stellar evolution manager"""

    logger.info("********************************************************")
    logger.info("          Stellar Evolution Database Manager            ")
    logger.info("********************************************************")
    logger.info("initialize database manager for stellar evolution models")

    # catch CTRL-C signal
    signal.signal(signal.SIGINT, __signal_handler)

    # current working directory
    curr_dir = os.getcwd()

    logger.info(f"current working directory is `{curr_dir}`")
    logger.info(f"{platform.python_implementation()} {platform.python_version()} detected")

    # # load main driver
    global core
    core = Manager()

    # start manager
    start()

    # start loop
    watch()

    # shutdown
    end()
