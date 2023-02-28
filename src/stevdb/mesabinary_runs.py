"""
Module that manages a set of MESAbinary simulations
"""

import glob
import re
import subprocess
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
from .mesa import NoMESArun


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
        drop_tables: bool = True,
        template_directory: Union[str, Path] = "",
        runs_directory: Union[str, Path] = "",
        mesa_binary_dict: dict = {},
        stevdb_dict: dict = {},
    ) -> None:

        self.replace_evolutions = replace_evolutions

        self.database_name = database_name
        self.drop_tables = drop_tables

        self.template_directory = template_directory
        self.runs_directory = runs_directory

        self.mesa_binary_dict = mesa_binary_dict
        self.stevdb_dict = stevdb_dict

        self.runs = self._get_list_of_models()

        # control when to create the header of the database tables
        self.doing_first_model_of_summary = True
        self.have_initials_table = False
        self.have_finals_table = False
        self.have_corecollapse_table = False

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

    def update_list_of_models(self) -> None:
        """Update the list of models to summarize"""

        self.runs = self._get_list_of_models()

    def run1_summary(self, run_name: str = "") -> MESArun:
        """Create single run summary"""

        if run_name == "":
            logger.error("empty string for `run_name`")

        # (tstart) to control amount of time of loading and processing MESA output
        tstart = time.time()

        logger.debug(f"inspecting run (id): `{run_name}`")

        RunSummary = MESArun(
            template_directory=self.template_directory,
            run_root_directory=self.runs_directory,
            run_name=run_name,
            is_binary_evolution=True,
            **self.mesa_binary_dict,
        )

        RunSummary.set_id(database_name=self.database_name)

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

            if "core-collapse" in RunSummary.Finals.get("condition"):
                core_collapse_dict = self.__load_history_columns_dict(key="corecollapse")
                RunSummary.get_core_collapse(history_columns_dict=core_collapse_dict)

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

        # tracking initial conditions ? create table
        if self.stevdb_dict.get("track_initials") and not self.have_initials_table:
            create_database(
                database_filename=self.database_name,
                table_name=self.stevdb_dict.get("id_for_initials_in_database"),
                drop_table=self.drop_tables,
                table_dict=runSummary.Initials,
            )
            self.have_initials_table = True

        # tracking final conditions ? create table
        if self.stevdb_dict.get("track_finals") and not self.have_finals_table:
            create_database(
                database_filename=self.database_name,
                table_name=self.stevdb_dict.get("id_for_finals_in_database"),
                drop_table=self.drop_tables,
                table_dict=runSummary.Finals,
            )
            self.have_finals_table = True

        # core-collapse table for first model
        if "core-collapse" in runSummary.Finals.get("condition") and not self.have_corecollapse_table:
            create_database(
                database_filename=self.database_name,
                table_name=self.stevdb_dict.get("id_for_core_collapse_in_database"),
                drop_table=self.drop_tables,
                table_dict=runSummary.CoreCollapse,
            )
            self.have_corecollapse_table = True

        # tracking XRB phase conditions ? create table
        if self.stevdb_dict.get("track_xrb_phase"):
            logger.error("`track_xrb_phase` not ready to be used")

        # tracking CE phase conditions ? create table
        if self.stevdb_dict.get("track_xrb_phase"):
            logger.error("`track_ce_phase` not ready to be used")

        # next, insert data into tables, if tracking is enabled
        if self.stevdb_dict.get("track_initials"):
            insert_run_into_database(
                database_filename=self.database_name,
                table_name=self.stevdb_dict.get("id_for_initials_in_database"),
                table_dict=runSummary.Initials,
            )

        # tracking final condition, save to database
        if self.stevdb_dict.get("track_finals"):
            # avoid saving None values in database of Finals
            insert_run_into_database(
                database_filename=self.database_name,
                table_name=self.stevdb_dict.get("id_for_finals_in_database"),
                table_dict=runSummary.Finals,
            )

            if "core-collapse" in runSummary.Finals.get("condition"):
                insert_run_into_database(
                    database_filename=self.database_name,
                    table_name=self.stevdb_dict.get("id_for_core_collapse_in_database"),
                    table_dict=runSummary.CoreCollapse,
                )

    def do_run_summary(self) -> None:
        """Create a summary of runs"""

        logger.debug("doing summary of run(s)")

        # loop over entire set of simulations
        for k, run in enumerate(self.runs):

            # output a nice progress bar in the terminal
            right_msg = f" {k+1}/{len(self.runs)} done"
            progress_bar(k, len(self.runs) - 1, left_msg="creating summary", right_msg=right_msg)

            # get name of MESA run
            name = run.split("/")[-2]

            try:
                Summary = self.run1_summary(run_name=name)

            except (NoMESArun, NotImplementedError):
                continue

            # if no exception was triggered, create database (if needed) and insert data into it
            else:
                self.do_summary_info(runSummary=Summary)

                # before the end of the first evaluation in the for-loop, we set this flag to False in order to avoid
                # creating the database header again
                if self.doing_first_model_of_summary:
                    self.doing_first_model_of_summary = False

        print()

    def database_control_versioning(self, commit_msg: str = "") -> None:
        """Version control of database to a given URL

        Parameters
        ----------
        commit_msg : `str`
            Message to add in the commit
        """

        # need path & name of database file
        p = Path(self.database_name)
        db_directory = str(p.parent)
        db_name = str(p.name)

        # first, run `git add {database_name}` command
        try:
            p = subprocess.Popen(
                f"git add {db_name}",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                cwd=db_directory,
            )
            stdout, stderr = p.communicate()
        except Exception:
            logger.error("could not add database file to git repo")
            return

        if stderr is None:
            logger.info("succesfully added database to git repository")

        # next, commit changes to repo
        if commit_msg == "":
            commit_msg = "database updated (auto commit message)"
        try:
            p = subprocess.Popen(
                f"git commit -m '{commit_msg}'",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                cwd=db_directory,
            )
            stdout, stderr = p.communicate()
        except Exception:
            logger.error("could not commit changes to git repo")
            return

        if stderr is None:
            logger.info("succesfully commited changes to git repository")

        # finally, push changes to remote repo
        try:
            p = subprocess.Popen(
                "git push origin main",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                cwd=db_directory,
            )
            stdout, stderr = p.communicate()
        except Exception:
            logger.error("could not push changes to git repo")
            return

        if stderr is None:
            logger.info("succesfully pushed changes to remote repository")

    def __load_history_columns_dict(self, key: str = "") -> dict:
        """Load dictionary with names of MESA history_columns.list to track initial conditions"""
        return load_yaml(fname=self.stevdb_dict.get("history_columns_list")).get(key)
