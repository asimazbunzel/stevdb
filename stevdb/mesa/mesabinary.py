"""
Module that manages a set of MESAbinary simulations
"""

from typing import Any, Dict, List, Set, Union

import glob
import re
import sys
import time
from pathlib import Path

import numpy as np

from stevdb.io import Database, load_yaml, logger, progress_bar

from .model import MESAmodel, MESAmodelAlreadyPresent, NoMESAmodel


class MESAbinaryGrid:
    """Class responsible of managing a set of MESAbinary simulations

    It controls the creation of additional tables in a database already created by the STEVMA
    stellar-evolution manager. These tables contain information regarding different stages in the
    evolution of isolated binaries from its start (as defined by the MESA code) until its end.

    In particular, it can provide information of a core-collapse happening at the end of the
    evolution of one star in the binary, as well as the stage in which a compact-object is emitting
    X-rays due to the release of accretion energy. Moreover, if the binary goes through a
    common-envelope phase this will also be stored in the database with important quantities during
    that phase evolution.

    Parameters
    ----------
    replace_models : `bool`
        Flag that controls the replacing of stellar-evolution models in all the tables of the
        database

    database_name : `str`
        Name of the database file

    stevma_table_name : `str`
        Name of the table inside `database_name` that was created by the STEVMA stellar-evolution
        manager

    template_directory : `str / Path`
        Location of template directory with the MESA source code specific of the grid of MESAbinary
        models

    runs_directory : `str / Path`
        Location of runs directory with the (potential) output of the MESAbinary models

    mesa_binary_dict : `dict`
        Dictionary with options that will be used to make a summary of MESAbinary models. In it,
        information on the type of models computed and output filenames must be stored (see example
        file)

    stevdb_dict : `dict`
        Dictionary with options for the making of tables in the database. In general, this
        dictionary will have which stages will be saved, and the name of the values coming from the
        MESAbinary models (see example file)
    """

    def __init__(
        self,
        replace_models: bool = False,
        database_name: str = "",
        stevma_table_name: str = "",
        template_directory: Union[str, Path] = "",
        runs_directory: Union[str, Path] = "",
        mesa_binary_dict: Dict[Any, Any] = {},
        stevdb_dict: Dict[Any, Any] = {},
    ) -> None:

        logger.info("setting up MESAbinaryGrid")

        # database controls
        self.replace_models = replace_models
        self.database_name = database_name
        self.stevma_table_name = stevma_table_name

        # load database as an object
        self.database = Database(database_name=self.database_name)

        # directories used by the MESA code
        self.template_directory = template_directory
        self.runs_directory = runs_directory

        # dictionaries with misc options
        self.mesa_binary_dict = mesa_binary_dict
        self.stevdb_dict = stevdb_dict

        # list of models inside self.runs_directory
        self.models = self._get_list_of_models()
        self.models_in_db: List[str] = list()

        # controls when to create the header of the database tables
        self.doing_first_model_of_summary = True
        self.create_header_MESAmodels = True
        self.create_header_Initials = True
        self.create_header_XRB = True
        self.create_header_CE = True
        self.create_header_Finals = True

    def _get_list_of_models(self) -> List[Union[str, Path]]:
        """List all the models to (potentially) be summarized

        Method that checks for the number of models to make a summary and returns the complete
        directory path

        Returns
        -------
        models_list : `list`
            List of models in runs_directory
        """

        logger.debug("getting list of MESAbinary models")

        if not Path(self.runs_directory).exists():
            logger.critical(f"no such directory found: `{self.runs_directory}`")
            sys.exit(1)

        # first, count items inside path
        directory_items = glob.glob(f"{self.runs_directory}/*/")

        # check if there are files that are named as `inlist*` which would mean that this is
        # the directory of a single stellar evolution model
        regex = re.compile("inlist")
        matches = [string for string in directory_items if re.match(regex, string)]

        models_list = []
        n: int
        if len(matches) > 0:
            n = 1
            logger.debug(f"only one ({n}) stellar evolution model found in `{self.runs_directory}`")

            models_list.append(self.runs_directory)
        else:
            n = len(directory_items)
            logger.debug(f"{n} stellar evolution models found in `{self.runs_directory}`")

            for item in directory_items:
                models_list.append(item)

        return models_list

    def update_list_of_models(self) -> None:
        """Update the list of models to summarize"""

        self.models = self._get_list_of_models()

    def append_model_to_list_of_models_in_db(self, model_name: str = "") -> None:
        """Update list of models already summarized"""

        self.models_in_db.append(model_name)

    def run1_summary(self, model_name: str = "") -> MESAmodel:
        """Create single MESAbinary model summary

        Parameters
        ----------
        model_name : `str`
            Name of MESAbinary model
        """

        if model_name == "":
            logger.error("empty string for `model_name`")
            raise NoMESAmodel(f"`{model_name}` is an empty string !")

        # (_startTime) to control amount of time of loading and processing MESA output
        _startTime = time.time()

        logger.debug(f"inspecting model (name): `{model_name}`")

        # get id from the table of models created with stevma (must have)
        model_id: int = self.database.get_id(
            table_name=self.stevma_table_name, model_name=model_name
        )

        if model_id == -1:
            raise NoMESAmodel(f"`{model_name}` does not have id found in database")

        # find if data is already present in the tables of the database (apart from stevma one)
        model_has_initial_data: bool = self.database.model_present(
            model_id=model_id,
            table_name=str(self.stevdb_dict.get("id_for_initials_in_database")),
        )
        model_has_xrb_data: bool = self.database.model_present(
            model_id=model_id,
            table_name=str(self.stevdb_dict.get("id_for_xrb_phase_in_database")),
        )
        model_has_final_data: bool = self.database.model_present(
            model_id=model_id,
            table_name=str(self.stevdb_dict.get("id_for_finals_in_database")),
        )

        if (
            model_has_initial_data
            and model_has_final_data
            and model_has_xrb_data
            and not self.replace_models
        ):
            raise MESAmodelAlreadyPresent(f"`{model_name}` is already present in database")

        modelSummary = MESAmodel(
            model_id=model_id,
            template_directory=self.template_directory,
            run_root_directory=self.runs_directory,
            model_name=model_name,
            insert_in_database=True,
            update_in_database=False,
            database_name=self.database_name,
            is_binary_evolution=True,
            **self.mesa_binary_dict,
        )
        modelSummary.have_initial_data = model_has_initial_data
        modelSummary.have_xrb_data = model_has_xrb_data
        modelSummary.have_final_data = model_has_final_data

        # check if simulation has actual MESA output, else do not try to make a summary of them
        if modelSummary.should_have_mesabinary and not modelSummary.have_mesabinary:
            logger.info(" model does not have MESAbinary output. skipping it")
            raise NoMESAmodel(f"`{model_name}` does not have MESAbinary output")

        if modelSummary.should_have_mesastar1 and not modelSummary.have_mesastar1:
            logger.info(" model does not have MESAstar1 output. skipping it")
            raise NoMESAmodel(f"`{model_name}` does not have MESAstar1 output")

        if modelSummary.should_have_mesastar2 and not modelSummary.have_mesastar2:
            logger.info(" model does not have MESAstar2 output. skipping it")
            raise NoMESAmodel(f"`{model_name}` does not have MESAstar2 output")

        # always grab first the termination_code string. if there is no file, skip its summary
        modelSummary.get_termination_code()
        if "None" in modelSummary.termination_code:
            logger.info(
                " model does not have a termination code: `{modelSummary.termination_code}`. "
                "skipping it"
            )
            raise NoMESAmodel(f"`{model_name}` does not have termination code")

        # initial conditions of binary system
        if self.stevdb_dict.get("track_initials"):
            initials_dict = self.__load_history_columns_dict(key="initials")
            modelSummary.get_initials(history_columns_dict=initials_dict)

        # final conditions of binary system
        if self.stevdb_dict.get("track_finals"):
            finals_dict = self.__load_history_columns_dict(key="finals")
            modelSummary.get_finals(history_columns_dict=finals_dict)

        if self.stevdb_dict.get("track_xrb_phase"):
            xrb_dict = self.__load_history_columns_dict(key="xrb")
            modelSummary.get_xrb_phase(history_columns_dict=xrb_dict)

        if self.stevdb_dict.get("track_ce_phase"):
            raise NotImplementedError("`track_ce_phase` is not ready to be used")

        # this controls whether the sqlite command is an insert or an update
        if False and model_has_final_data:
            modelSummary.update_in_database = True
            modelSummary.insert_in_database = False

        # (tend) to control loading and processing time
        _endTime = time.time()
        logger.debug(f" [loading and processing time of MESA run: {_endTime-_startTime:.2f} sec]")

        return modelSummary

    def do_summary_info(self, modelSummary: MESAmodel = None) -> None:  # type: ignore
        """Write summary of a MESA model into database"""

        logger.debug(f"inserting into database, model (name): `{modelSummary.model_name}`")

        # tracking initial conditions ? create table
        if self.create_header_Initials and self.stevdb_dict.get("track_initials"):
            self.database.create_table(
                table_name=str(self.stevdb_dict.get("id_for_initials_in_database")),
                table_data_dict=modelSummary.Initials,
            )
            self.create_header_Initials = False

        # tracking final conditions ? create table
        if self.create_header_Finals and self.stevdb_dict.get("track_finals"):
            self.database.create_table(
                table_name=str(self.stevdb_dict.get("id_for_finals_in_database")),
                table_data_dict=modelSummary.Finals,
            )
            self.create_header_Finals = False

        # tracking XRB phase conditions ? create table
        if self.create_header_XRB and self.stevdb_dict.get("track_xrb_phase"):
            self.database.create_table(
                table_name=str(self.stevdb_dict.get("id_for_xrb_phase_in_database")),
                table_data_dict=modelSummary.XRB,
            )
            self.create_header_XRB = False

        # tracking CE phase conditions ? create table
        if self.create_header_CE and self.stevdb_dict.get("track_ce_phase"):
            logger.error("`track_ce_phase` not ready to be used")

        # next, insert data into tables, if tracking is enabled
        if self.stevdb_dict.get("track_initials"):
            if not modelSummary.have_initial_data:
                self.database.insert_record(
                    table_name=str(self.stevdb_dict.get("id_for_initials_in_database")),
                    table_data_dict=modelSummary.Initials,
                )
            elif self.replace_models:
                self.database.update_record(
                    table_name=str(self.stevdb_dict.get("id_for_initials_in_database")),
                    table_data_dict=modelSummary.Initials,
                    model_id=modelSummary.model_id,
                )

        # track XRB phase conditions, save to database
        if self.stevdb_dict.get("track_xrb_phase"):
            # the outputted dictionary with XRB phase properties are arrays
            # so first check the length of any of them
            add_record = True
            for value in modelSummary.XRB.values():
                if isinstance(value, np.ndarray):
                    if len(value) <= 0:
                        add_record = False
                        break

            if add_record:
                if not modelSummary.have_xrb_data:
                    self.database.insert_record(
                        table_name=str(self.stevdb_dict.get("id_for_xrb_phase_in_database")),
                        table_data_dict=modelSummary.XRB,
                    )
                elif self.replace_models:
                    self.database.update_record(
                        table_name=str(self.stevdb_dict.get("id_for_xrb_phase_in_database")),
                        table_data_dict=modelSummary.XRB,
                        model_id=modelSummary.model_id,
                    )

        # tracking final condition, save to database
        if self.stevdb_dict.get("track_finals"):
            # there could be cases where the final conditions have None values
            # those should not be added
            add_record = True
            for value in modelSummary.Finals.values():
                if value is None:
                    add_record = False
                    break

            if add_record:
                if not modelSummary.have_final_data:
                    self.database.insert_record(
                        table_name=str(self.stevdb_dict.get("id_for_finals_in_database")),
                        table_data_dict=modelSummary.Finals,
                    )
                elif self.replace_models:
                    self.database.update_record(
                        table_name=str(self.stevdb_dict.get("id_for_finals_in_database")),
                        table_data_dict=modelSummary.Finals,
                        model_id=modelSummary.model_id,
                    )

        # change status from STEVMA table
        self.database.update_model_status(
            table_name=str(self.stevma_table_name),
            model_name=modelSummary.model_name,
            status="completed",
        )

    def do_run_summary(self) -> None:
        """Create a summary of models"""

        logger.debug("doing summary of MESAbinary model(s)")

        # loop over entire set of models
        for k, model in enumerate(self.models):

            # output a nice progress bar in the terminal
            right_msg = f" {k+1}/{len(self.models)} done"
            progress_bar(k + 1, len(self.models), left_msg="summary progress", right_msg=right_msg)

            # get name of MESA model
            name = str(model).split("/")[-2]

            try:
                Summary = self.run1_summary(model_name=name)

            except (NoMESAmodel, NotImplementedError, MESAmodelAlreadyPresent):
                logger.info(
                    f" either model not found, found but not going to replace or requested "
                    f"feature not implemented yet: `{name}`"
                )
                continue

            # if no exception was triggered, create table (if needed) and insert data into it
            else:

                self.do_summary_info(modelSummary=Summary)

                self.append_model_to_list_of_models_in_db(model_name=str(model))

                # before the end of the first evaluation in the for-loop, we set this flag to False
                # in order to avoid creating the database header again
                if self.doing_first_model_of_summary:
                    self.doing_first_model_of_summary = False

        print()

    def need_to_update_database(self) -> bool:
        """Utility method to know if there is a new model to append into database tables"""

        need_update = False

        # new list of models (self.models updated)
        self.update_list_of_models()

        if len(self.models) > len(self.models_in_db):
            need_update = True

        elif len(self.models) < len(self.models_in_db):
            logger.critical("new list of runs is less than earlier. something is VERY WRONG")
            sys.exit(1)

        return need_update

    def new_models_to_append(self) -> Set[Union[str, Path]]:
        """Get new models to append to database

        Returns
        -------
        List with new models to append
        """

        # find which elements are new
        previous_set = set(self.models_in_db)
        new_set = set(self.models)
        unique_models = new_set.difference(previous_set)

        return unique_models

    def __load_history_columns_dict(self, key: str = "") -> Any:
        """Load dictionary with names of MESA history_columns.list to track initial conditions

        Parameters
        ----------
        key : `str`
            Key related to stage of binary evolution for which MESA output will be stored in the
            database

        Returns
        -------
        Dictionary with valid output of a MESA history_columns.list file
        """

        return load_yaml(fname=str(self.stevdb_dict.get("history_columns_list"))).get(key)
