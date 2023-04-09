"""Module driver to make a summary of a MESA simulation
"""

from typing import Any, Dict, Union

import os
import sys
from pathlib import Path

from stevdb.io import logger

from .defaults import get_mesa_defaults
from .mesa import MESAdata


class NoMESAmodel(Exception):
    """Object for case of no MESA model"""

    pass


class MESAmodelAlreadyPresent(Exception):
    """Object for cases where a MESA model is already present in database"""

    pass


class MESAmodel:
    """Object matching a single MESA model

    It contains information on the model as well as a summary of important parameters

    Parameters
    ----------
    model_id : `int`
        Integer identifier coming from database (table created by STEVMA code)

    template_directory : `str / Path`
        Directory location of the template used in the run

    run_directory : `str / Path`
        The location where the output of MESA is located

    model_name : `str`
        Name of the directory where the output of MESA is located

    write_to_database : `bool`
        Flag to write model into database tables

    is_binary_evolution: `bool`
        Flag to set/unset binary evolution

    **kwargs : `dict`
        Misc dictionary with more options
    """

    def __init__(  # type: ignore
        self,
        model_id: int = -1,
        template_directory: Union[str, Path] = "",
        run_root_directory: Union[str, Path] = "",
        model_name: str = "",
        insert_in_database: bool = True,
        update_in_database: bool = False,
        is_binary_evolution: bool = True,
        **kwargs,
    ) -> None:

        logger.debug(" initializing MESArun")

        self.model_id = model_id

        logger.debug(f"  `model_id`: {self.model_id}")

        # let directories be handled by pathlib module
        if isinstance(template_directory, str):
            self.template_directory = Path(template_directory)
        else:
            self.template_directory = template_directory
        if isinstance(run_root_directory, str):
            self.run_root_directory = Path(run_root_directory)
        else:
            self.run_root_directory = run_root_directory

        logger.debug(f"  `template_directory`: {self.template_directory}")
        logger.debug(f"  `run_root_directory`: {self.run_root_directory}")

        # name of the directory containing the output of MESA
        self.model_name = model_name
        logger.debug(f"  `model_name: {self.model_name}")

        # whether to insert of update information on database. this is used outside of this module
        # (see mesabinary module)
        self.insert_in_database = insert_in_database
        self.update_in_database = update_in_database

        # flag to know the type of MESA module used in the simulation
        self.is_binary_evolution = is_binary_evolution
        logger.debug(f"  `is_binary_evolution: {self.is_binary_evolution}")

        # flags for MESAstar & MESAbinary. if run has only one star (MESAstar or MESAbinary
        # but with one star and a point-mass), use `*_mesastar_1`
        self.should_have_mesabinary = False
        self.should_have_mesastar1 = True
        self.should_have_mesastar2 = False
        self.have_mesabinary = False
        self.have_mesastar1 = False
        self.have_mesastar2 = False

        # MESAbinary run, should have MESAbinary output
        if self.is_binary_evolution:
            self.should_have_mesabinary = True

        logger.debug(f"  `should_have_mesabinary`: {self.should_have_mesabinary}")
        logger.debug(f"  `should_have_mesastar1`: {self.should_have_mesastar1}")

        # flag to control the type of MESAbinary run
        if "evolve_both_stars" in kwargs.keys():
            evolve_both_stars = kwargs.get("evolve_both_stars")
            if evolve_both_stars:
                self.should_have_mesastar2 = True
        else:
            if self.is_binary_evolution:
                logger.error("MESAbinary simulation require `evolve_both_stars` set in config file")
                sys.exit(1)

        logger.debug(f"  `should_have_mesastar2`: {self.should_have_mesastar2}")

        # flags to know if simulation has ended or not, based on the termination_file existance
        self.should_have_termination_file = True
        self.have_termination_file = False

        # location of MESA install
        if "mesa_dir" in kwargs.keys():
            self.mesa_dir = kwargs.get("mesa_dir")
        else:
            self.mesa_dir = os.environ.get("MESA_DIR")
            if self.mesa_dir is None:
                raise ValueError("need `mesa_dir` variable to make a summary of a simulation")

        logger.debug(f"  `mesa_dir`: {self.mesa_dir}")
        logger.debug(f"  MESAbinary flags (should_have): {self.should_have_mesabinary}")
        logger.debug(f"  MESAstar1 flags (should_have): {self.should_have_mesastar1}")
        logger.debug(f"  MESAstar2 flags (should_have): {self.should_have_mesastar2}")

        # _MESA*History contains the output of a MESA simulation saved in the MESAdata object
        self._MESAbinaryHistory = None
        self._MESAstar1History = None
        self._MESAstar2History = None

        # actual load of MESA output
        self._load_MESA_output(kwargs)

        # load MESA default options into a dictionary
        self._MESADefaults = get_mesa_defaults(mesa_dir=self.mesa_dir)  # type: ignore

    def _load_MESA_output(self, kwargs: Dict[Any, Any]) -> None:
        """Load MESA output"""

        logger.debug(" loading MESA output")

        # depending on the type of run, load specific MESAstar/binary output
        if self.should_have_mesabinary:
            log_directory_binary: str = str(kwargs.get("log_directory_binary"))
            history_name_binary: str = str(kwargs.get("history_name_binary"))
            try:
                fname_binary = (
                    Path(self.run_root_directory)
                    / Path(self.model_name)
                    / Path(log_directory_binary)
                    / Path(history_name_binary)
                )
            except TypeError:
                logger.error(
                    "Need complete path to binary_history filename to load MESA output and some "
                    "of them are missing. Please check if `log_directory_binary` and "
                    "`history_name_binary` are set in the configuration file"
                )
                sys.exit(1)

            if not fname_binary.is_file() and not Path(f"{str(fname_binary)}.gz").is_file():
                logger.debug(
                    f"  MESA output for binary does not exist (file: `{str(fname_binary)}`)"
                )

        # star 1 output
        if self.should_have_mesastar1:
            log_directory_star1: str = str(kwargs.get("log_directory_star1"))
            history_name_star1: str = str(kwargs.get("history_name_star1"))
            try:
                fname_star1 = (
                    Path(self.run_root_directory)
                    / Path(self.model_name)
                    / Path(log_directory_star1)
                    / Path(history_name_star1)
                )
            except TypeError:
                logger.error(
                    "Need complete path to (star1) history filename to load MESA output and some "
                    "of them are missing. Please check if `log_directory_star1` and "
                    "`history_name_star1` are set in the configuration file"
                )
                sys.exit(1)

            if not fname_star1.is_file() and not Path(f"{str(fname_star1)}.gz").is_file():
                logger.debug(f"  MESA output for star1 does not exist (file: `{str(fname_star1)}`)")

        # star2 output
        if self.should_have_mesastar2:
            log_directory_star2: str = str(kwargs.get("log_directory_star2"))
            history_name_star2: str = str(kwargs.get("history_name_star2"))
            try:
                fname_star2 = (
                    Path(self.run_root_directory)
                    / Path(self.model_name)
                    / Path(log_directory_star2)
                    / Path(history_name_star2)
                )
            except TypeError:
                logger.error(
                    "Need complete path to (star2) history filename to load MESA output and some "
                    "of them are missing. Please check if `log_directory_star2` and "
                    "`history_name_star2` are set in the configuration file"
                )
                sys.exit(1)

            if not fname_star2.is_file() and not Path(f"{str(fname_star2)}.gz").is_file():
                logger.debug(f"  MESA output for star2 does not exist (file: `{str(fname_star2)}`)")

        # termination code of the simulation
        termination_directory = str(kwargs.get("termination_directory"))
        termination_name = str(kwargs.get("termination_name"))
        try:
            termination_fname = (
                Path(self.run_root_directory)
                / Path(self.model_name)
                / Path(termination_directory)
                / Path(termination_name)
            )
        except TypeError:
            logger.error(
                "Need complete path to termination filename to load MESA output and some of them "
                "are missing. Please check if `termination_directory` and `termination_name` are "
                "set in the configuration file"
            )
            sys.exit(1)

        if not termination_fname.is_file():
            logger.debug(
                f"  file with termination code does not exist (file: `{str(termination_fname)}`)"
            )

        # core-collapse info (in case simulation has reached that stage)
        core_collapse_directory: str = str(kwargs.get("core_collapse_directory"))
        if self.should_have_mesabinary:
            core_collapse_name_binary = str(kwargs.get("core_collapse_name_binary"))
            try:
                fname_binary_cc = (
                    Path(self.run_root_directory)
                    / Path(self.model_name)
                    / Path(core_collapse_directory)
                    / Path(core_collapse_name_binary)
                )
            except TypeError:
                logger.error(
                    "Need complete path to (binary) core-collapse filename to load MESA output "
                    "and some of them are missing. Please check if `core_collapse_directory` and "
                    "`core_collapse_name_binary` are set in the configuration file"
                )
                sys.exit(1)

        if self.should_have_mesastar1:
            core_collapse_name_star1: str = str(kwargs.get("core_collapse_name_star1"))
            try:
                fname_star1_cc = (
                    Path(self.run_root_directory)
                    / Path(self.model_name)
                    / Path(core_collapse_directory)
                    / Path(core_collapse_name_star1)
                )
            except TypeError:
                logger.error(
                    "Need complete path to (star1) core-collapse filename to load MESA output "
                    "and some of them are missing. Please check if `core_collapse_directory` and "
                    "`core_collapse_name_star1` are set in the configuration file"
                )
                sys.exit(1)

        if self.should_have_mesastar2:
            core_collapse_name_star2: str = str(kwargs.get("core_collapse_name_star2"))
            try:
                fname_star2_cc = (
                    Path(self.run_root_directory)
                    / Path(self.model_name)
                    / Path(core_collapse_directory)
                    / Path(core_collapse_name_star2)
                )
            except TypeError:
                logger.error(
                    "Need complete path to (star2) core-collapse filename to load MESA output "
                    "and some of them are missing. Please check if `core_collapse_directory` and "
                    "`core_collapse_name_star2` are set in the configuration file"
                )
                sys.exit(1)

        # load MESAbinary stuff
        if self.should_have_mesabinary:
            try:
                self._MESAbinaryHistory = MESAdata(  # type: ignore
                    history_name=fname_binary,
                    termination_name=str(termination_fname),
                    core_collapse_name=fname_binary_cc,
                    mesa_dir=self.mesa_dir,  # type: ignore
                )
            except FileNotFoundError:
                pass
        if self.should_have_mesastar1:
            try:
                self._MESAstar1History = MESAdata(  # type: ignore
                    history_name=fname_star1,
                    termination_name=str(termination_fname),
                    core_collapse_name=fname_star1_cc,
                    mesa_dir=self.mesa_dir,  # type: ignore
                )
            except FileNotFoundError:
                pass
        if self.should_have_mesastar2:
            try:
                self._MESAstar2History = MESAdata(  # type: ignore
                    history_name=fname_star2,
                    termination_name=str(termination_fname),
                    core_collapse_name=fname_star2_cc,
                    mesa_dir=self.mesa_dir,  # type: ignore
                )
            except FileNotFoundError:
                pass

        if self._MESAbinaryHistory is not None:
            self.have_mesabinary = True  # type: ignore
        if self._MESAstar1History is not None:
            self.have_mesastar1 = True  # type: ignore
        if self._MESAstar2History is not None:
            self.have_mesastar2 = True  # type: ignore

        logger.debug(f"   MESAbinary flags (have): {self.have_mesabinary}")
        logger.debug(f"   MESAstar1 flags (have): {self.have_mesastar1}")
        logger.debug(f"   MESAstar2 flags (have): {self.have_mesastar2}")

    def get_termination_code(self) -> None:
        """Set the value of the termination_code string of a MESA simulation"""

        logger.debug(" getting termination condition (code) of MESAmodel")

        if self.have_mesabinary:
            self.termination_code = self._MESAbinaryHistory.termination_code  # type: ignore

        elif self.have_mesastar1:
            self.termination_code = self._MESAstar1History.termination_code  # type: ignore

        elif self.have_mesastar2:
            self.termination_code = self._MESAstar2History.termination_code  # type: ignore

        else:
            logger.error(
                "`have_mesabinary`, `have_mesastar1` and `have_mesastar2` are all false at the "
                "same time ! something is not right"
            )
            sys.exit(1)

        logger.debug(f"  termination code found: `{self.termination_code}`")

    def get_initials(self, history_columns_dict: Dict[Any, Any] = {}) -> None:
        """Get initial conditions of a MESA model

        Parameters
        ----------
        history_columns_list : `dict`
            Dictionary with the MESA column names to search for initial conditions
        """

        logger.debug(" getting initial conditions of MESAmodel")

        if "star" not in history_columns_dict and "binary" not in history_columns_dict:
            logger.error("`history_columns_list` must contain either the `star` or `binary` keys")
            sys.exit(1)

        initials: Dict[Any, Any] = dict()

        # store location of run and template as it might be important when looking for profiles
        # as PosixPath is not considered a string, we change it here just to avoid conflicts when
        # saving info into a database
        initials["model_id"] = self.model_id
        initials["template_directory"] = str(self.template_directory)
        initials["run_root_directory"] = str(self.run_root_directory)
        initials["is_binary_evolution"] = self.is_binary_evolution

        # search for star conditions
        if "star" in history_columns_dict:
            if self.have_mesastar1:
                for name in history_columns_dict.get("star"):  # type: ignore
                    try:
                        initials[f"{name}_1"] = self._MESAstar1History.get(name)[0]  # type: ignore
                    except KeyError:
                        logger.debug(f"   could not find `{name}` in star1 MESA output")
                    except IndexError:
                        initials[f"{name}_1"] = self._MESAstar1History.get(name)  # type: ignore

            if self.have_mesastar2:
                for name in history_columns_dict.get("star"):  # type: ignore
                    try:
                        initials[f"{name}_2"] = self._MESAstar2History.get(name)[0]  # type: ignore
                    except KeyError:
                        logger.debug(f"   could not find `{name}` in star2 MESA output")
                    except IndexError:
                        initials[f"{name}_2"] = self._MESAstar2History.get(name)  # type: ignore

        if "binary" in history_columns_dict:
            if self.have_mesabinary:
                for name in history_columns_dict.get("binary"):  # type: ignore
                    try:
                        initials[name] = self._MESAbinaryHistory.get(name)[0]  # type: ignore
                    except KeyError:
                        logger.debug(f"   could not find `{name}` in binary MESA output")
                    except IndexError:
                        initials[name] = self._MESAbinaryHistory.get(name)  # type: ignore

        self.Initials = initials

        logger.debug(f"  initial conditions found: {self.Initials}")

    def get_finals(self, history_columns_dict: Dict[Any, Any] = {}) -> None:
        """Get final conditions of a MESA model

        Parameters
        ----------
        history_columns_list : `dict`
            Dictionary with the core-collapse (custom MESA module) column names to search for
            final conditions
        """

        logger.debug(" getting final conditions of MESAmodel")

        if "star" not in history_columns_dict and "binary" not in history_columns_dict:
            logger.error("`history_columns_list` must contain either the `star` or `binary` keys")
            sys.exit(1)

        finals = dict()

        # need run_name when saving Final values
        finals["model_id"] = self.model_id

        # search for star conditions
        if "star" in history_columns_dict:
            if self.have_mesastar1:
                for name in history_columns_dict.get("star"):  # type: ignore
                    try:
                        finals[f"{name}_1"] = self._MESAstar1History.get(name)  # type: ignore
                    except KeyError:
                        logger.debug(f"   could not find `{name}` in star1 MESA output")
                        finals[f"{name}_1"] = None  # type: ignore

            if self.have_mesastar2:
                for name in history_columns_dict.get("star"):  # type: ignore
                    try:
                        finals[f"{name}_2"] = self._MESAstar2History.get(name)  # type: ignore
                    except KeyError:
                        logger.debug(f"   could not find `{name}` in star2 MESA output")
                        finals[f"{name}_2"] = None  # type: ignore

        if "binary" in history_columns_dict:
            if self.have_mesabinary:
                for name in history_columns_dict.get("binary"):  # type: ignore
                    try:
                        finals[name] = self._MESAbinaryHistory.get(name)  # type: ignore
                    except KeyError:
                        logger.debug(f"   could not find `{name}` in binary MESA output")
                        finals[name] = None  # type: ignore

        self.Finals = finals

        logger.debug(f"  final conditions found: {self.Finals}")
