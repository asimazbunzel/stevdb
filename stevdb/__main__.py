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
from stevdb.mesa import MESAbinaryGrid
from stevdb.mesa.model import MESAmodelAlreadyPresent, NoMESAmodel


def __signal_handler(signal, frame) -> None:
    """Callback for CTRL-C"""

    end()


def end() -> None:
    """Stop manager"""

    print("shutting down")

    # time it
    _endTime = time.time()

    logger.info(f"[-- manager uptime: {_endTime - _startTime:.2f} sec --]")
    logger.info("manager stopped")

    sys.exit(0)


def watch():
    """Manager will be updated in this loop"""

    # useful shortcuts
    admin_dict: dict = core.config.get("Admin")

    # first thing, make a summary of each simulation
    gridManager.do_run_summary()
    # gridManager.copy_models_list()

    # keep on going with manager being active
    print("STEVDB in watch mode", end="...", flush=True)
    keep_alive: bool = True
    while keep_alive:

        # wait a while before updating list of runs
        logger.info(
            f"manager will now enter into waiting mode for {admin_dict.get('waiting_time_in_sec')} sec"
        )
        time.sleep(admin_dict.get("waiting_time_in_sec"))

        need_update = gridManager.need_to_update_database()
        if need_update:

            # get list of new models
            new_models = gridManager.new_models_to_append()
            logger.info(f"new runs to include into database: {str(new_models)}")

            # loop through new model to append to database using single methods of the MESAbinaryGrid class
            for model in new_models:

                # remove absolute path, get directory name where model is located
                name = model.split("/")[-2]

                # create summary
                try:
                    Summary = gridManager.run1_summary(model_name=name)

                except (NoMESAmodel, NotImplementedError, MESAmodelAlreadyPresent):
                    logger.info(
                        f" either model not found, found but not going to replace or requested "
                        f"feature not implemented yet: `{name}`"
                    )

                except NotImplementedError:
                    continue

                # if no exception was triggered, insert data into it
                else:
                    gridManager.do_summary_info(modelSummary=Summary)

                    gridManager.append_model_to_list_of_models_in_db(model_name=model)

        else:
            logger.info("no new models found ! continue waiting")


def start() -> None:
    """Start manager"""

    logger.info("manager started")

    # time it
    global _startTime
    _startTime = time.time()

    # if only want to print database name and exit
    if core.args.log_fname:
        print(f"LOG FILENAME is: `{LOG_FILENAME}`")
        end()

    # show config and exit
    if core.args.show_config:
        pprint.pprint(core.config)
        end()

    # useful shortcuts
    admin_dict: dict = core.config.get("Admin")
    mesa_dict: dict = core.config.get("MESA")
    stevdb_dict: dict = core.config.get("Stevdb")

    # set up the grid manager
    if mesa_dict.get("id") == "mesabinary":
        global gridManager
        gridManager = MESAbinaryGrid(
            replace_models=admin_dict.get("replace_models"),
            database_name=admin_dict.get("database_name"),
            stevma_table_name=admin_dict.get("stevma_table_name"),
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
    watch()


if __name__ == "__main__":
    main()
