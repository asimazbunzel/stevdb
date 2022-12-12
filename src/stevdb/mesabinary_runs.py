"""
Module that manages a set of MESAbinary simulations
"""

from collections import OrderedDict
import glob
import os
from pathlib import Path, PosixPath
import re
import sqlite3
import sys
from typing import Union

import numpy as np

from .io.logger import LOG_FILENAME, logger
from .io.io import progress_bar
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
    """

    def __init__(self, replace_evolutions: bool = False, database_name: str = "", overwrite_database: bool = True, template_directory: Union[str, Path] = "", runs_directory: Union[str, Path] = "", mesa_binary_dict: dict = {}) -> None:

        self.replace_evolutions = replace_evolutions

        self.database_name = database_name
        self.overwrite_database = overwrite_database

        self.template_directory = template_directory
        self.runs_directory = runs_directory

        self.mesa_binary_dict = mesa_binary_dict

        self.runs = self._get_list_of_models()

    def _get_list_of_models(self) -> list:
        """List models to summarize
        Method that checks for the number of simulations to make a summary and returns the complete folder path

        Returns
        -------
        runs_list : `list`
            List of simulations in runs_directory
        """

        if not Path(self.runs_directory).exists():
            logger.critical(f"no such folder found: `{runs_directory}`")
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
            logger.debug(
                f"only one (n = {n}) stellar evolution model found in `{self.runs_directory}`"
            )

            runs_list.append(self.runs_directory)
        else:
            n = len(folder_items)
            logger.debug(
                f"n = {n} stellar evolution models found in `{self.runs_directory}`"
            )

            for item in folder_items:
                runs_list.append(item)

        return runs_list

    def create_summary(self):
        """Create a summary of runs"""

        for k, run in enumerate(self.runs):
            right_msg = f" {k+1}/{len(self.runs)} done"
            progress_bar(
                k, len(self.runs), left_msg="creating summary", right_msg=right_msg
            )

            logger.debug(f"inspecting folder: `{run.split('/')[-2]}`")

            name = run.split("/")[-2]
            self.MESAsummary = MESArun(
                template_directory=self.template_directory,
                run_directory=self.runs_directory,
                run_name=name,
                is_binary_evolution=True,
                **self.mesa_binary_dict,
            )

            if self.MESAsummary.should_have_mesabinary and not self.MESAsummary.have_mesabinary:
                logger.info("simulation does not have MESAbinary output. skipping it")
                continue

            # initial conditions of binary system
            self.MESAsummary.get_initial_conditions()

            self.MESAsummary.get_termination_code()

            sys.exit(0)
