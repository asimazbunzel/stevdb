"""Module driver to make a summary of a MESA simulation

Depending on the type of simulation to summarize (isolated or binary) different
methods are available

Isolated star methods:

    - get_star_initial_conditions()

Binary methods:

    - get_binary_initial_conditions()

Note that for a binary case, isolated methods will be available for one or two stars
depending on the type of binary simulation (two stars or one and a point-mass)
"""

import os
import sys
from pathlib import Path
from typing import Union

from ..io.database import load_database
from ..io.logger import logger
from .defaults import get_mesa_defaults
from .mesa import MESAdata


class NoMESArun(Exception):
    pass


class MESArun(object):
    """Object matching a single MESA run

    It contains information on the run as well as a summary of important parameters

    Parameters
    ----------
    template_directory : `str / Path`
        Folder location of the template used in the run
    run_directory : `str / Path`
        The location where the output of MESA is located
    run_name : `str`
        Name of the folder where the output of MESA is located
    """

    def __init__(
        self,
        template_directory: Union[str, Path] = "",
        run_root_directory: Union[str, Path] = "",
        run_name: str = "",
        is_binary_evolution: bool = True,
        **kwargs,
    ) -> None:

        logger.debug(" initializing MESArun")

        # let folders be handled by pathlib module
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

        # name of the folder containing the output of MESA
        self.run_name = run_name
        logger.debug(f"  `run_name: {self.run_name}")

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

        # location of MESA_DIR install
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
        self._MESADefaults = get_mesa_defaults(mesa_dir=self.mesa_dir)

    def _load_MESA_output(self, kwargs):
        """Load MESA output"""

        logger.debug(" loading MESA output")

        # depending on the type of run, load specific MESAstar/binary output
        if self.should_have_mesabinary:
            log_directory_binary = kwargs.get("log_directory_binary")
            history_name_binary = kwargs.get("history_name_binary")
            try:
                fname_binary = Path(self.run_root_directory) / Path(self.run_name) / Path(log_directory_binary) / Path(history_name_binary)
            except TypeError:
                logger.error(
                    "Need complete path to binary_history filename to load MESA output and some of them are missing. "
                    "Please check if `log_directory_binary` and `history_name_binary` are set in the configuration file"
                )
                sys.exit(1)

            if not fname_binary.is_file() and not Path(f"{str(fname_binary)}.gz").is_file():
                logger.debug(f"  MESA output for binary does not exist (file: `{str(fname_binary)}`)")

        # star 1 output
        if self.should_have_mesastar1:
            log_directory_star1 = kwargs.get("log_directory_star1")
            history_name_star1 = kwargs.get("history_name_star1")
            try:
                fname_star1 = Path(self.run_root_directory) / Path(self.run_name) / Path(log_directory_star1) / Path(history_name_star1)
            except TypeError:
                logger.error(
                    "Need complete path to (star1) history filename to load MESA output and some of them are missing. "
                    "Please check if `log_directory_star1` and `history_name_star1` are set in the configuration file"
                )
                sys.exit(1)

            if not fname_star1.is_file() and not Path(f"{str(fname_star1)}.gz").is_file():
                logger.debug(f"  MESA output for star1 does not exist (file: `{str(fname_star1)}`)")

        # star2 output
        if self.should_have_mesastar2:
            log_directory_star2 = kwargs.get("log_directory_star2")
            history_name_star2 = kwargs.get("history_name_star2")
            try:
                fname_star2 = Path(self.run_root_directory) / Path(self.run_name) / Path(log_directory_star2) / Path(history_name_star2)
            except TypeError:
                logger.error(
                    "Need complete path to (star2) history filename to load MESA output and some of them are missing. "
                    "Please check if `log_directory_star2` and `history_name_star2` are set in the configuration file"
                )
                sys.exit(1)

            if not fname_star2.is_file() and not Path(f"{str(fname_star2)}.gz").is_file():
                logger.debug(f"  MESA output for star2 does not exist (file: `{str(fname_star2)}`)")

        # termination code of the simulation
        termination_directory = kwargs.get("termination_directory")
        termination_name = kwargs.get("termination_name")
        try:
            termination_fname = Path(self.run_root_directory) / Path(self.run_name) / Path(termination_directory) / Path(termination_name)
        except TypeError:
            logger.error(
                "Need complete path to termination filename to load MESA output and some of them are missing. "
                "Please check if `termination_directory` and `termination_name` are set in the configuration file"
            )
            sys.exit(1)

        if not termination_fname.is_file():
            logger.debug(f"  file with termination code does not exist (file: `{str(termination_fname)}`)")

        # core-collapse info (in case simulation has reached that stage)
        core_collapse_directory = kwargs.get("core_collapse_directory")
        if self.should_have_mesabinary:
            core_collapse_name_binary = kwargs.get("core_collapse_name_binary")
            try:
                fname_binary_cc = (
                    Path(self.run_root_directory) / Path(self.run_name) / Path(core_collapse_directory) / Path(core_collapse_name_binary)
                )
            except TypeError:
                logger.error(
                    "Need complete path to (binary) core-collapse filename to load MESA output and some of them are missing. "
                    "Please check if `core_collapse_directory` and `core_collapse_name_binary` are set in the configuration file"
                )
                sys.exit(1)

        if self.should_have_mesastar1:
            core_collapse_name_star1 = kwargs.get("core_collapse_name_star1")
            try:
                fname_star1_cc = (
                    Path(self.run_root_directory) / Path(self.run_name) / Path(core_collapse_directory) / Path(core_collapse_name_star1)
                )
            except TypeError:
                logger.error(
                    "Need complete path to (star1) core-collapse filename to load MESA output and some of them are missing. "
                    "Please check if `core_collapse_directory` and `core_collapse_name_star1` are set in the configuration file"
                )
                sys.exit(1)

        if self.should_have_mesastar2:
            core_collapse_name_star2 = kwargs.get("core_collapse_name_star2")
            try:
                fname_star2_cc = (
                    Path(self.run_root_directory) / Path(self.run_name) / Path(core_collapse_directory) / Path(core_collapse_name_star2)
                )
            except TypeError:
                logger.error(
                    "Need complete path to (star2) core-collapse filename to load MESA output and some of them are missing. "
                    "Please check if `core_collapse_directory` and `core_collapse_name_star2` are set in the configuration file"
                )
                sys.exit(1)

        # load MESAbinary stuff
        if self.should_have_mesabinary:
            try:
                self._MESAbinaryHistory = MESAdata(
                    history_name=fname_binary,
                    termination_name=str(termination_fname),
                    core_collapse_name=fname_binary_cc,
                    mesa_dir=self.mesa_dir,
                )
            except FileNotFoundError:
                pass
        if self.should_have_mesastar1:
            try:
                self._MESAstar1History = MESAdata(
                    history_name=fname_star1,
                    termination_name=str(termination_fname),
                    core_collapse_name=fname_star1_cc,
                    mesa_dir=self.mesa_dir,
                )
            except FileNotFoundError:
                pass
        if self.should_have_mesastar2:
            try:
                self._MESAstar2History = MESAdata(
                    history_name=fname_star2,
                    termination_name=str(termination_fname),
                    core_collapse_name=fname_star2_cc,
                    mesa_dir=self.mesa_dir,
                )
            except FileNotFoundError:
                pass

        if self._MESAbinaryHistory is not None:
            self.have_mesabinary = True
        if self._MESAstar1History is not None:
            self.have_mesastar1 = True
        if self._MESAstar2History is not None:
            self.have_mesastar2 = True

        logger.debug(f"   MESAbinary flags (have): {self.have_mesabinary}")
        logger.debug(f"   MESAstar1 flags (have): {self.have_mesastar1}")
        logger.debug(f"   MESAstar2 flags (have): {self.have_mesastar2}")

    def get_termination_code(self) -> None:
        """Set the value of the termination_code string of a MESA simulation"""

        logger.debug(" getting termination condition (code) of MESArun")

        if self.have_mesabinary:
            self.termination_code = self._MESAbinaryHistory.termination_code

        elif self.have_mesastar1:
            self.termination_code = self._MESAstar1History.termination_code

        elif self.have_mesastar2:
            self.termination_code = self._MESAstar2History.termination_code

        else:
            logger.error("`have_mesabinary`, `have_mesastar1` and `have_mesastar2` are all false at the same time ! something is not right")
            sys.exit(1)

    def set_id(self, database_name: Union[str, Path] = "") -> None:
        """Get ID of a MESA run from a database table"""

        self.run_id = load_database(database_filename=database_name, table_name="MESAruns", run_name=self.run_name)

        return None

    def get_initials(self, history_columns_dict: dict = {}) -> None:
        """Get initial conditions of a MESA run

        Parameters
        ----------
        history_columns_list : `dict`
            Dictionary with the MESA column names to search for initial conditions
        """

        logger.debug(" getting initial conditions of MESArun")

        if "star" not in history_columns_dict and "binary" not in history_columns_dict:
            logger.error("`history_columns_list` must contain either the `star` or `binary` keys")
            sys.exit(1)

        self.Initials = self._get_dict_values_for_summary(history_columns_dict=history_columns_dict)

        # also add id to dict
        self.Initials["id"] = self.run_id

    def get_finals(self, history_columns_dict: dict = {}) -> None:
        """Get final conditions of a MESA run

        Parameters
        ----------
        history_columns_list : `dict`
            Dictionary with the core-collapse (custom MESA module) column names to search for final conditions
        """

        logger.debug(" getting final conditions of MESArun")

        if "star" not in history_columns_dict and "binary" not in history_columns_dict:
            logger.error("`history_columns_list` must contain either the `star` or `binary` keys")
            sys.exit(1)

        self.Finals = self._get_dict_values_for_summary(history_columns_dict=history_columns_dict)

        # also add id to dict
        self.Finals["id"] = self.run_id

    def get_core_collapse(self, history_columns_dict: dict = {}) -> None:
        """Get conditions at core-collapse of a MESA run

        Parameters
        ----------
        history_columns_list : `dict`
            Dictionary with the core-collapse (custom MESA module) column names to search for final conditions
        """

        logger.debug(" getting core-collapse conditions of MESArun")

        if "star" not in history_columns_dict and "binary" not in history_columns_dict:
            logger.error("`history_columns_list` must contain either the `star` or `binary` keys")
            sys.exit(1)

        self.CoreCollapse = self._get_dict_values_for_summary(history_columns_dict=history_columns_dict)

        # also add id to dict
        self.CoreCollapse["id"] = self.run_id

    def _get_dict_values_for_summary(self, history_columns_dict: dict = {}) -> dict:
        """Get values from a MESA run and store them into a dict

        Parameters
        ----------
        history_columns_list : `dict`
            Dictionary with the core-collapse (custom MESA module) column names to search for final conditions
        """

        dictValues = dict()

        # search for star conditions
        if "star" in history_columns_dict:
            if self.have_mesastar1:
                for name in history_columns_dict.get("star"):
                    # patch for supernova model to work without changing too much the logic
                    if name == "sn_model":
                        dictValues[f"{name}_1"] = self._MESAstar1History.get(name)
                    else:
                        try:
                            dictValues[f"{name}_1"] = self._MESAstar1History.get(name)[0]
                        except KeyError:
                            logger.debug(f"   could not find `{name}` in star1 MESA output")
                            dictValues[f"{name}_1"] = None
                        except (IndexError, TypeError):
                            dictValues[name] = self._MESAstar1History.get(name)

            if self.have_mesastar2:
                for name in history_columns_dict.get("star"):
                    try:
                        dictValues[f"{name}_2"] = self._MESAstar2History.get(name)[0]
                    except KeyError:
                        logger.debug(f"   could not find `{name}` in star2 MESA output")
                        dictValues[f"{name}_2"] = None
                    except (IndexError, TypeError):
                        dictValues[name] = self._MESAstar2History.get(name)

        if "binary" in history_columns_dict:
            if self.have_mesabinary:
                for name in history_columns_dict.get("binary"):
                    try:
                        dictValues[name] = self._MESAbinaryHistory.get(name)[0]
                    except KeyError:
                        logger.debug(f"   could not find `{name}` in binary MESA output")
                        dictValues[name] = None
                    except (IndexError, TypeError):
                        dictValues[name] = self._MESAbinaryHistory.get(name)

        if "misc" in history_columns_dict:
            for name in history_columns_dict.get("misc"):
                if name == "status":
                    dictValues[name] = "finished"
                elif name == "condition":
                    dictValues[name] = self._MESAbinaryHistory.termination_code
                else:
                    logger.debug(f"   could not find `{name}` in MESA output")
                    dictValues[name] = None

        return dictValues
