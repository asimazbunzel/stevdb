"""
Module that manages a set of MESAbinary simulations
"""

from typing import Union

import glob
import os
import re
import sys
import time
from pathlib import Path

from stevdb.io import Database, load_yaml, logger, progress_bar

from .model import MESArun, MESArunAlreadyPresent, NoMESArun


class MESAbinaryGrid:
    """Class responsible of managing a set of MESAbinary simulations

    It controls the creation of additional tables in a database already created by the STEVMA stellar-evolution manager. These tables contain information regarding different stages in the evolution of isolated binaries from its start (as defined by the MESA code) until its end.

    In particular, it can provide information of a core-collapse happening at the end of the evolution of one star in the binary, as well as the stage in which a compact-object is emitting X-rays due to the release of accretion energy. Moreover, if the binary goes through a common-envelope phase this will also be stored in the database with important quantities during that phase evolution.

    Parameters
    ----------
    replace_models : `bool`
        Flag that controls the replacing of stellar-evolution models in all the tables of the database

    database_name : `str`
        Name of the database file

    stevma_table_name : `str`
        Name of the table inside `database_name` that was created by the STEVMA stellar-evolution manager

    template_directory : `str / Path`
        Location of template directory with the MESA source code specific of the grid of MESAbinary models

    runs_directory : `str / Path`
        Location of runs directory with the (potential) output of the MESAbinary models

    mesa_binary_dict : `dict`
        Dictionary with options that will be used to make a summary of MESAbinary models. In it, information on the type of models computed and output filenames must be stored (see example file)

    stevdb_dict : `dict`
        Dictionary with options for the making of tables in the database. In general, this dictionary will have which stages will be saved, and the name of the values coming from the MESAbinary models (see example file)
    """

    def __init__(
        self,
        replace_models: bool = False,
        database_name: str = "",
        stevma_table_name: str = "",
        template_directory: Union[str, Path] = "",
        runs_directory: Union[str, Path] = "",
        mesa_binary_dict: dict = {},
        stevdb_dict: dict = {},
    ) -> None:

        logger.info("setting up MESAbinaryGrid")

        # database controls
        self.replace_models = replace_models
        self.database_name = database_name
        self.stevma_table_name = stevma_table_name

        # load database as an object
        self.database = Database(database_name=self.database_name)

        self.template_directory = template_directory
        self.runs_directory = runs_directory

        self.mesa_binary_dict = mesa_binary_dict
        self.stevdb_dict = stevdb_dict

        self.runs = self._get_list_of_models()

        # control when to create the header of the database tables
        self.doing_first_model_of_summary = True

    def _get_list_of_models(self) -> list:
        """List models to summarize
        Method that checks for the number of simulations to make a summary and returns the complete
        folder path

        Returns
        -------
        runs_list : `list`
            List of simulations in runs_directory
        """

        logger.debug("getting list of MESAbinary models")

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
        n: int
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

    def update_list_of_models(self) -> None:
        """Update the list of models to summarize"""

        self.runs = self._get_list_of_models()

    def run1_summary(self, run_name: str = "") -> MESArun:
        """Create single run summary"""

        if run_name == "":
            logger.error("empty string for `run_name`")
            raise NoMESArun(f"`{run_name}` is an empty string !")

        # (tstart) to control amount of time of loading and processing MESA output
        tstart = time.time()

        logger.debug(f"inspecting run (id): `{run_name}`")

        # get id from the table of runs created with stevma (must have)
        run_id: int = self.database.get_id(table_name=self.stevma_table_name, run_name=run_name)

        if run_id == -1:
            logger.info(" id not found in database")
            raise NoMESArun(f"`{run_name}` does not have id found in database")

        # find if data is already present in the tables of the database (apart from stevma one)
        run_id_has_final_data: bool = self.database.model_present(
            run_id=run_id,
            table_name=self.stevdb_dict.get("id_for_finals_in_database"),
        )
        if run_id_has_final_data and not self.replace_models:
            raise MESArunAlreadyPresent(f"`{run_name}` is already present in database")

        RunSummary = MESArun(
            run_id=run_id,
            template_directory=self.template_directory,
            run_root_directory=self.runs_directory,
            run_name=run_name,
            database_name=self.database_name,
            is_binary_evolution=True,
            **self.mesa_binary_dict,
        )

        # check if simulation has actual MESA output, else do not try to make a summary of them
        if RunSummary.should_have_mesabinary and not RunSummary.have_mesabinary:
            logger.info(" simulation does not have MESAbinary output. skipping it")
            raise NoMESArun(f"`{run_name}` does not have MESAbinary output")

        if RunSummary.should_have_mesastar1 and not RunSummary.have_mesastar1:
            logger.info(" simulation does not have MESAstar1 output. skipping it")
            raise NoMESArun(f"`{run_name}` does not have MESAstar1 output")

        if RunSummary.should_have_mesastar2 and not RunSummary.have_mesastar2:
            logger.info(" simulation does not have MESAstar2 output. skipping it")
            raise NoMESArun(f"`{run_name}` does not have MESAstar2 output")

        # always grab first the termination_code string. if there is no file, skip its summary
        RunSummary.get_termination_code()
        if "unknown (None)" in RunSummary.termination_code:
            logger.info(" simulation does not have a termination code. skipping it")
            raise NoMESArun(f"`{run_name}` does not have termination code")

        # initial conditions of binary system
        if self.stevdb_dict.get("track_initials"):
            initials_dict = self.__load_history_columns_dict(key="initials")
            RunSummary.get_initials(history_columns_dict=initials_dict)

        # final conditions of binary system
        if self.stevdb_dict.get("track_finals"):
            finals_dict = self.__load_history_columns_dict(key="finals")
            RunSummary.get_finals(history_columns_dict=finals_dict)

        if self.stevdb_dict.get("track_xrb_phase"):
            raise NotImplementedError("`track_xrb_phase` is not ready to used")

        if self.stevdb_dict.get("track_ce_phase"):
            raise NotImplementedError("`track_ce_phase` is not ready to be used")

        # (tend) to control loading and processing time
        tend = time.time()
        logger.debug(f" [loading and processing time of MESA run: {tend-tstart:.2f} sec]")

        return RunSummary

    def do_summary_info(self, runSummary: MESArun = None) -> None:
        """Write summary of a MESA simulation into database"""

        # create tables if this is the first model in the database
        if self.doing_first_model_of_summary:

            # tracking initial conditions ? create table
            if self.stevdb_dict.get("track_initials"):
                self.database.create_table(
                    table_name=self.stevdb_dict.get("id_for_initials_in_database"),
                    table_data_dict=runSummary.Initials,
                )

            # tracking final conditions ? create table
            if self.stevdb_dict.get("track_finals"):
                self.database.create_table(
                    table_name=self.stevdb_dict.get("id_for_finals_in_database"),
                    table_data_dict=runSummary.Finals,
                )

            # tracking XRB phase conditions ? create table
            if self.stevdb_dict.get("track_xrb_phase"):
                logger.error("`track_xrb_phase` not ready to be used")

            # tracking CE phase conditions ? create table
            if self.stevdb_dict.get("track_xrb_phase"):
                logger.error("`track_ce_phase` not ready to be used")

        # next, insert data into tables, if tracking is enabled
        if self.stevdb_dict.get("track_initials"):
            self.database.insert_record(
                table_name=self.stevdb_dict.get("id_for_initials_in_database"),
                table_data_dict=runSummary.Initials,
            )

        # tracking final condition, save to database
        if self.stevdb_dict.get("track_finals"):
            # avoid saving None values in database of Finals
            self.database.insert_record(
                table_name=self.stevdb_dict.get("id_for_finals_in_database"),
                table_data_dict=runSummary.Finals,
            )

        # change status from STEVMA table
        self.database.update_model_status(
            table_name=self.stevma_table_name, run_name=runSummary.run_name, status="completed"
        )

    def do_run_summary(self) -> None:
        """Create a summary of runs"""

        logger.debug("doing summary of MESAbinary run(s)")

        # loop over entire set of simulations
        for k, run in enumerate(self.runs):

            # output a nice progress bar in the terminal
            right_msg = f" {k+1}/{len(self.runs)} done"
            progress_bar(k + 1, len(self.runs), left_msg="creating summary", right_msg=right_msg)

            # get name of MESA run
            name = run.split("/")[-2]

            try:
                Summary = self.run1_summary(run_name=name)

            except (NoMESArun, NotImplementedError):
                continue

            # if no exception was triggered, create database (if needed) and insert data into it
            else:
                self.do_summary_info(runSummary=Summary)

                # before the end of the first evaluation in the for-loop, we set this flag to False
                # in order to avoid creating the database header again
                if self.doing_first_model_of_summary:
                    self.doing_first_model_of_summary = False

    def __load_history_columns_dict(self, key: str = "") -> dict:
        """Load dictionary with names of MESA history_columns.list to track initial conditions"""
        return load_yaml(fname=self.stevdb_dict.get("history_columns_list")).get(key)
