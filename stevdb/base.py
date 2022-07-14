"""Driver for the database of stellar models"""

import argparse
from collections import OrderedDict
import glob
import os
from pathlib import Path, PosixPath
import re
import sqlite3
import sys

import numpy as np
import pprint

from stevdb.io import load_yaml, logger, progress_bar
from stevdb.mesa import MESArun


class Manager(object):
    """Manager contains the configuration needed to create or update a database of stellar
    evolution models

    Parameters
    ----------
    """

    def __init__(self) -> None:

        # command line arguments
        self.args = self.parse_args()

        if self.args.config_fname is None:
            logger.critical(
                f"`configuration file option cannot be empty (maybe in the future we'll have defaults)`"
            )
            sys.exit(1)

        # always use pathlib
        if isinstance(self.args.config_fname, str):
            if len(self.args.config_fname) == 0:
                logger.critical("empty configuration file not available right now")
                sys.exit(1)

            self.args.config_fname = Path(self.args.config_fname)

        # load configuration
        self.config = self.load_config_file()

        # list of stellar evolution model names
        self.runs = self.get_list_of_models()

        # go through items in self.runs and make a summary of each of the evolutions
        self.create_summary()

    def init_args(self) -> argparse.ArgumentParser:
        """Initialize parser of command line arguments"""

        parser = argparse.ArgumentParser(
            prog="db-manager",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="create and/or update a database of stellar evolution simulations",
        )

        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            default=False,
            dest="debug",
            help="enable debug mode",
        )

        parser.add_argument(
            "-C",
            "--config-file",
            dest="config_fname",
            help="name of configuration file",
        )

        parser.add_argument(
            "--show-log-name",
            action="store_true",
            default=False,
            dest="log_fname",
            help="display log filename and exit",
        )

        return parser

    def parse_args(self) -> argparse.Namespace:
        """Parse command line arguments"""

        args = self.init_args().parse_args()

        if args.debug:
            from logging import DEBUG

            logger.setLevel(DEBUG)

        # print cli arguments to log file
        msg = "command line arguments are: "
        for k, v in sorted(vars(args).items()):
            msg += f"{k}: {v} "
        logger.debug(msg[:-1])

        return args

    def load_config_file(self) -> dict:
        """Load configuration file with options for the manager"""

        logger.info("load configuration options from file")

        if not self.args.config_fname.exists():
            logger.critical(f"no such file found: `{self.args.config_fname}`")
            sys.exit(1)

        return load_yaml(self.args.config_fname)

    def get_list_of_models(self) -> list:
        """List models to summarize

        Method that checks for the number of simulations to make a summary and returns the complete
        folder path
        """

        # useful dictionary
        mesaDict = self.config.get("MESA")
        runs_directory = mesaDict.get("runs_directory")

        if not Path(runs_directory).exists():
            logger.critical(f"no such folder found: `{runs_directory}`")
            sys.exit(1)

        # first, count items inside path
        folder_items = glob.glob(f"{runs_directory}/*/")

        # check if there are files that are named as `inlist*` which would mean that this is
        # the folder of a single stellar evolution model
        regex = re.compile("inlist")
        matches = [string for string in folder_items if re.match(regex, string)]

        run_list = []
        if len(matches) > 0:
            n = 1
            logger.debug(
                f"only one (n = {n}) stellar evolution model found in `{runs_directory}`"
            )

            run_list.append(runs_directory)
        else:
            n = len(folder_items)
            logger.debug(
                f"n = {n} stellar evolution models found in `{runs_directory}`"
            )

            for item in folder_items:
                run_list.append(item)

        return run_list

    def create_summary(self) -> None:
        """Create a summary of runs"""

        # useful dictionary
        mesaDict = self.config.get("MESA")
        runs_directory = mesaDict.get("runs_directory")

        # to control the creation of the database
        create_database = True

        for k, run in enumerate(self.runs):

            right_msg = f" {k+1}/{len(self.runs)} done"
            progress_bar(k, len(self.runs), left_msg="creating summary", right_msg=right_msg)

            logger.debug(f"inspecting folder: `{run.split('/')[-2]}`")

            name = run.split("/")[-2]
            self.MESAsummary = MESArun(
                template_directory="/home/asimazbunzel/Projects/HMXB-NSBH/data/raw/templates",
                run_directory="/home/asimazbunzel/Projects/HMXB-NSBH/data/raw/runs",
                run_name=name,
                is_binary_evolution=True,
            )

            # get initial stuff of the run
            self.MESAsummary.get_initial_conditions()

            # get termination condition
            self.MESAsummary.get_termination_condition()
            self.MESAsummary.get_pre_collapse_conditions()
            self.MESAsummary.get_collapse_conditions()

            # get stuff during a XRB phase
            self.MESAsummary.get_xrb_phase_conditions()

            if create_database:
                self.create_database(table_dict=self.MESAsummary.ordered_dict())
                create_database = False

            self.insert_run_into_database(table_dict=self.MESAsummary.ordered_dict())

        print()


    def create_database(self, table_dict: OrderedDict = OrderedDict()) -> None:
        """Create database of stellar evolution simulations with summaries"""

        logger.debug("creating database")

        # maps between python and sqlite
        dtype_map = {
            None: "NULL",
            int: "INTEGER",
            float: "REAL",
            np.float64: "REAL",
            str: "TEXT",
            bytes: "BLOB",
            bool: "INTEGER",
        }

        # useful dictionary
        adminDict = self.config.get("Admin")

        if not adminDict.get("overwrite_database"):
            return None
        else:
            try:
                os.remove(adminDict.get("database_name"))
            except Exception as e:
                logger.info("not going to remove database. file does not exist")

        # create database
        conn = sqlite3.connect(adminDict.get("database_name"))

        # connect to it with a cursor
        c = conn.cursor()

        command = "CREATE TABLE IF NOT EXISTS MESArun ("
        command_core_collapse = "CREATE TABLE IF NOT EXISTS MESArunCC (run_name TEXT, "
        command_xray_phase = "CREATE TABLE IF NOT EXISTS MESArunXRB (id INTEGER PRIMARY KEY, run_name TEXT, "
        for key, value in table_dict.items():

            # dictionaries go into another table
            if isinstance(value, dict):
                for mkey, mvalue in value.items():
                    # if it is a dictionary, store value in MESArun table
                    if isinstance(mvalue, dict):
                        # if core-collapse, store in table of core_collapse
                        if "core_collapse" in mkey:
                            for mmkey, mmvalue in mvalue.items():
                                command_core_collapse += f"{mmkey} {dtype_map[type(mmvalue)]}, "

                        elif "xrb_phase" in mkey:
                            for mmkey, mmvalue in mvalue.items():
                                # this is a dictionary with the key being the id of the XRB phase
                                k = mmkey

                                for mmmkey, mmmvalue in mmvalue.items():
                                    if mmmkey in ("mt_case", "mt_type", "spectral_type"):
                                        command_xray_phase += f"{mmmkey} TEXT, "
                                        continue

                                    if isinstance(mmmvalue, (list, np.ndarray)):
                                        command_xray_phase += f"{mmmkey} REAL, "

                                    else:
                                        command_xray_phase += f"{mmmkey} {dtype_map[type(mmmvalue)]}, "

                    else:
                        # sometimes there is a None in the list, skip it
                        if mvalue is None:
                            logger.error(f"None value found for key: {mkey} not going to add it")
                            continue

                        else:
                            command += f"{mkey} {dtype_map[type(mvalue)]}, "

                continue

            if isinstance(value, PosixPath):
                value = str(value)
                command += f"{key} {dtype_map[type(value)]}, "

            else:
                command += f"{key} {dtype_map[type(value)]}, "

        # create table
        command = command[:-2]
        command += ");"
        c.execute(command)

        command_core_collapse = command_core_collapse[:-2]
        command_core_collapse += ");"
        c.execute(command_core_collapse)

        command_xray_phase = command_xray_phase[:-2]
        command_xray_phase += ");"
        c.execute(command_xray_phase)

        # commit changes
        conn.commit()

        # close connection
        conn.close()

    def insert_run_into_database(self, table_dict: OrderedDict = OrderedDict()) -> None:
        """Insert record to database"""

        # useful dictionary
        adminDict = self.config.get("Admin")

        # create database
        conn = sqlite3.connect(adminDict.get("database_name"))

        # connect to it with a cursor
        c = conn.cursor()

        # text for SQLite to insert rows into tables of database
        command = "INSERT INTO MESArun"
        command_core_collapse = "INSERT INTO MESArunCC"
        command_col_names = "("
        command_col_values = "("
        command_col_names_core_collapse = "(run_name, "
        command_col_values_core_collapse = f"('{table_dict.get('run_name')}', "

        for key, value in table_dict.items():
            # dictionaries go into another table
            if isinstance(value, dict):
                for mkey, mvalue in value.items():
                    # if it is a dictionary, store value in MESArun table
                    if isinstance(mvalue, dict):
                        # if core-collapse, store in table of core_collapse
                        if "core_collapse" in mkey:
                            for mmkey, mmvalue in mvalue.items():
                                command_col_names_core_collapse += f"{mmkey}, "
                                if isinstance(mmvalue, str):
                                    mmvalue = f"'{mmvalue}'"
                                command_col_values_core_collapse += f"{mmvalue}, "

                        elif "xrb_phase" in mkey:
                            for mmkey, mmvalue in mvalue.items():
                                # this is a dictionary with the key being the id of the XRB phase
                                k = mmkey

                                # this is the number of elements in the arrays of the XRB phase summary
                                n_items = len(mmvalue.get("timestep"))

                                for i in range(n_items):
                                    # text for SQLite to insert rows into tables of database
                                    command_xray_phase = "INSERT INTO MESArunXRB"
                                    command_col_names_xray_phase = "(run_name, "
                                    command_col_values_xray_phase = f"('{table_dict.get('run_name')}', "

                                    for mmmkey, mmmvalue in mmvalue.items():
                                        command_col_names_xray_phase += f"{mmmkey}, "
                                        if mmmkey in ("mt_case", "mt_type"):
                                            command_col_values_xray_phase += f"'{mmmvalue}', "
                                            continue

                                        if isinstance(mmmvalue, (list, np.ndarray)):
                                            if isinstance(mmmvalue[i], str):
                                                command_col_values_xray_phase += f"'{mmmvalue[i]}', "
                                            else:
                                                command_col_values_xray_phase += f"{mmmvalue[i]}, "
                                        else:
                                            command_col_values_xray_phase += f"{mmmvalue}, "

                                    # write into xray table just after looping
                                    command_xray_phase = f"{command_xray_phase} {command_col_names_xray_phase[:-2]}) values {command_col_values_xray_phase[:-2]})"
                                    if "None" in command_xray_phase:
                                        skip_write_to_xray_phase_table = True
                                    else:
                                        skip_write_to_xray_phase_table = False

                                    if not skip_write_to_xray_phase_table:
                                        c.execute(command_xray_phase)

                    else:
                        if "xrb_phase" in mkey:
                            logger.debug("xray_phase item not belonging here. skipping it")
                            continue

                        if isinstance(mvalue, bool):
                            if mvalue:
                                mvalue = 1
                            else:
                                mvalue = 0
                        command_col_names += f"{mkey}, "
                        command_col_values += f"'{mvalue}', "

            elif isinstance(value, PosixPath) or isinstance(value, str):
                value = str(value)
                command_col_names += f"{key}, "
                command_col_values += f"'{value}', "

            elif isinstance(value, bool):
                if value:
                    value = 1
                else:
                    value = 0
                command_col_names += f"{key}, "
                command_col_values += f"{value}, "

            else:
                command_col_names += f"{key}, "
                command_col_values += f"{value}, "


        # write row to MESArun database
        command = f"{command} {command_col_names[:-2]}) VALUES {command_col_values[:-2]})"
        c.execute(command)

        # repeat but for core-collapse table of database
        command_core_collapse = f"{command_core_collapse} {command_col_names_core_collapse[:-2]}) values {command_col_values_core_collapse[:-2]})"

        # if we did not reach core-collapse, do not add it to that table
        if "None" in command_core_collapse:
            skip_write_to_core_collapse_table = True
        else:
            skip_write_to_core_collapse_table = False

        if not skip_write_to_core_collapse_table:
            c.execute(command_core_collapse)

        # commit changes
        conn.commit()

        # close connection
        conn.close()

    def show_database(self, name: str = "") -> None:
        """Show database information

        Mostly for debugging purposes
        """

        # useful dictionary
        adminDict = self.config.get("Admin")

        # create database connection
        conn = sqlite3.connect(adminDict.get("database_name"))

        # connect to it with a cursor
        c = conn.cursor()

        data = c.execute(f"SELECT * FROM {name}")

        for row in data:
            print(row)

        conn.close()
