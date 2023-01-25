"""
Module that manages a set of MESAbinary simulations
"""

import glob
import os
import re
import sys
import time
from pathlib import Path
from typing import Union

from .io.database import create_database
from .io.database import insert_run_into_database
from .io.io import load_yaml
from .io.io import progress_bar
from .io.logger import logger
from .mesa import MESArun


class MESAbinaryGrid(object):
    """Class responsible of managing a set of MESAbinary simulations

    Parameters
    ----------
    replace_evolutions : `bool`
        Flag that controls the replacing of evolutions in the database

    database_name : `string`
        Name of the database file

    overwrite_database : `bool`
        Flag to control whether to re-write database file

    template_directory : `str / Path`
        Location of template folder

    runs_directory : `str / Path`
        Location of runs folder

    mesa_binary_dict : `dict`
        TBD

    stevdb_dict : `dict`
        TBD
    """

    def __init__(
        self,
        replace_evolutions: bool = False,
        database_name: str = "",
        overwrite_database: bool = True,
        template_directory: Union[str, Path] = "",
        runs_directory: Union[str, Path] = "",
        mesa_binary_dict: dict = {},
        stevdb_dict: dict = {},
    ) -> None:

        self.replace_evolutions = replace_evolutions

        self.database_name = database_name
        self.overwrite_database = overwrite_database

        self.template_directory = template_directory
        self.runs_directory = runs_directory

        self.mesa_binary_dict = mesa_binary_dict
        self.stevdb_dict = stevdb_dict

        self.runs = self._get_list_of_models()

        # to overwrite database file, remove it first
        if self.overwrite_database:
            try:
                os.remove(database_name)
            except Exception:
                logger.info("not going to remove database. file does not exist")

    def _get_list_of_models(self) -> list:
        """List models to summarize
        Method that checks for the number of simulations to make a summary and returns the complete folder path

        Returns
        -------
        runs_list : `list`
            List of simulations in runs_directory
        """

        if not Path(self.runs_directory).exists():
            logger.critical(f"no such folder found: `{self.runs_directory}`")
            sys.exit(1)

        # first, count items inside path
        folder_items = glob.glob(f"{self.runs_directory}/*/")

        # check if there are files that are named as `inlist*` which would mean that this is
        # the folder of a single stellar evolution model
        regex = re.compile("inlist")
        matches = [string for string in folder_items if re.match(regex, string)]

        runs_list = []
        if len(matches) > 0:
            n = 1
            logger.debug(f"only one ({n}) stellar evolution model found in `{self.runs_directory}`")

            runs_list.append(self.runs_directory)
        else:
            n = len(folder_items)
            logger.debug(f"{n} stellar evolution models found in `{self.runs_directory}`")

            for item in folder_items:
                runs_list.append(item)

        return runs_list

    def create_summary(self):
        """Create a summary of runs"""

        # this flag helps to create database just once at the start
        doing_first_model_of_summary = True

        for k, run in enumerate(self.runs):

            # output a nice progress bar in the terminal
            right_msg = f" {k+1}/{len(self.runs)} done"
            progress_bar(k, len(self.runs), left_msg="creating summary", right_msg=right_msg)

            logger.debug(f"inspecting folder: `{run.split('/')[-2]}`")

            # (tstart) to control amount of time of loading and processing MESA output
            tstart = time.time()

            name = run.split("/")[-2]
            self.MESAsummary = MESArun(
                template_directory=self.template_directory,
                run_root_directory=self.runs_directory,
                run_name=name,
                is_binary_evolution=True,
                **self.mesa_binary_dict,
            )

            # check if simulation has actual MESA output, else do not try to make a summary of them
            if self.MESAsummary.should_have_mesabinary and not self.MESAsummary.have_mesabinary:
                logger.info(" simulation does not have MESAbinary output. skipping it")
                continue

            if self.MESAsummary.should_have_mesastar1 and not self.MESAsummary.have_mesastar1:
                logger.info(" simulation does not have MESAstar1 output. skipping it")
                continue

            if self.MESAsummary.should_have_mesastar2 and not self.MESAsummary.have_mesastar2:
                logger.info(" simulation does not have MESAstar2 output. skipping it")
                continue

            # always grab first the termination_code string. if there is no file, skip its summary
            self.MESAsummary.get_termination_code()
            if "unknown (None)" in self.MESAsummary.termination_code:
                logger.info(" simulation does not have a termination code. skipping it")
                continue

            # initial conditions of binary system
            if self.stevdb_dict.get("track_initials"):
                initials_dict = self.__load_history_columns_dict(key="initials")
                self.MESAsummary.get_initials(history_columns_dict=initials_dict)

                # create table with initials if this is the first model
                if doing_first_model_of_summary:
                    create_database(
                        database_filename=self.database_name,
                        table_name=self.stevdb_dict.get("id_for_initials_in_database"),
                        table_dict=self.MESAsummary.Initials,
                    )

                insert_run_into_database(
                    database_filename=self.database_name,
                    table_name=self.stevdb_dict.get("id_for_initials_in_database"),
                    table_dict=self.MESAsummary.Initials,
                )

            # final conditions of binary system
            if self.stevdb_dict.get("track_finals"):
                finals_dict = self.__load_history_columns_dict(key="finals")
                self.MESAsummary.get_finals(history_columns_dict=finals_dict)

                # create table with finals if this is the first model
                if doing_first_model_of_summary:
                    create_database(
                        database_filename=self.database_name,
                        table_name=self.stevdb_dict.get("id_for_finals_in_database"),
                        table_dict=self.MESAsummary.Finals,
                    )

                # avoid saving None values in database of Finals
                if all(self.MESAsummary.Finals.values()):
                    insert_run_into_database(
                        database_filename=self.database_name,
                        table_name=self.stevdb_dict.get("id_for_finals_in_database"),
                        table_dict=self.MESAsummary.Finals,
                    )

            # before the end of the first evaluation in the for-loop, we set this flag to False in order to avoid
            # creating the database header again
            doing_first_model_of_summary = False

            # (tend) to control loading and processing time
            tend = time.time()
            logger.debug(f" [loading and processing time of MESA run: {tend-tstart:.2f} sec]")

    def __load_history_columns_dict(self, key: str = "") -> dict:
        """Load dictionary with names of MESA history_columns.list to track initial conditions"""
        return load_yaml(fname=self.stevdb_dict.get("history_columns_list")).get(key)
