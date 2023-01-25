"""
Module that manages a set of MESAbinary simulations
"""

import glob

# import os
import re

# import sqlite3
import sys

# from collections import OrderedDict
from pathlib import Path

# from pathlib import PosixPath
from typing import Union

from .io.io import load_yaml
from .io.io import progress_bar
from .io.logger import logger
from .mesa import MESArun

# import numpy as np


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

        for k, run in enumerate(self.runs):
            right_msg = f" {k+1}/{len(self.runs)} done"
            progress_bar(k, len(self.runs), left_msg="creating summary", right_msg=right_msg)

            logger.debug(f"inspecting folder: `{run.split('/')[-2]}`")

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
                logger.info("simulation does not have MESAbinary output. skipping it")
                continue

            if self.MESAsummary.should_have_mesastar1 and not self.MESAsummary.have_mesastar1:
                logger.info("simulation does not have MESAstar1 output. skipping it")
                continue

            if self.MESAsummary.should_have_mesastar2 and not self.MESAsummary.have_mesastar2:
                logger.info("simulation does not have MESAstar2 output. skipping it")
                continue

            # always grab first the termination_code string
            self.MESAsummary.get_termination_code()

            # initial conditions of binary system
            if self.stevdb_dict.get("track_initials"):
                initials_dict = self.__load_history_columns_dict(key="initials")
                self.MESAsummary.get_initials(history_columns_dict=initials_dict)

            # self.MESAsummary.get_termination_code()
            # self.MESAsummary.get_xrb_phase()

            print("debugging summary of MESA run")
            sys.exit(0)

    def __load_history_columns_dict(self, key: str = "") -> dict:
        """Load dictionary with names of MESA history_columns.list to track initial conditions"""
        return load_yaml(fname=self.stevdb_dict.get("history_columns_list")).get(key)
