"""Module driver to make a summary of a MESA simulation"""

from collections import OrderedDict
from pathlib import Path
import sys
from typing import Union

from ..io.logger import logger
from .mesa import MESAbinary, MESAstar

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
        run_directory: Union[str, Path] = "",
        run_name: str = "",
        is_binary_evolution: bool = True,
        **kwargs,
    ) -> None:

        logger.info("loading MESArun")

        # let folders be handled by pathlib module
        if isinstance(template_directory, str):
            self.template_directory = Path(template_directory)
        else:
            self.template_directory = template_directory
        if isinstance(run_directory, str):
            self.run_directory = Path(run_directory)
        else:
            self.run_directory = run_directory

        # name of the folder containing the output of MESA
        self.run_name = run_name

        # flag to know the type of MESA module used in the simulation
        self.is_binary_evolution = is_binary_evolution

        # flags for MESAstar & MESAbinary. if run has only one star (MESAstar or MESAbinary
        # but with one star and a point-mass), use `*_mesastar_1`
        self.should_have_mesabinary = False
        self.should_have_mesastar1 = True
        self.should_have_mesastar2 = False
        self.have_mesabinary = False
        self.have_mesastar1 = False
        self.have_mesastar2 = False

        # MESAbinary run, should have MESAbinary output
        if self.is_binary_evolution: self.should_have_mesabinary = True

        # flag to control the type of MESAbinary run
        if "evolve_both_stars" in kwargs.keys():
            evolve_both_stars = kwargs.get("evolve_both_stars")
            if evolve_both_stars:
                self.should_have_mesastar2 = True
        else:
            if self.is_binary_evolution:
                logger.error("MESAbinary simulation require `evolve_both_stars` set in config file")
                sys.exit(0)

        logger.debug(f"MESAbinary flags (should_have, have): {self.should_have_mesabinary}, {self.have_mesabinary}")
        logger.debug(f"MESAstar1 flags (should_have, have): {self.should_have_mesastar1}, {self.have_mesastar1}")
        logger.debug(f"MESAstar2 flags (should_have, have): {self.should_have_mesastar2}, {self.have_mesastar2}")

        # depending on the type of run, load specific MESAstar/binary output
        if self.should_have_mesabinary:
            log_directory_binary = kwargs.get("log_directory_binary")
            history_name_binary = kwargs.get("history_name_binary")
            try:
                fname_binary = Path(self.run_directory) / Path(run_name) / Path(log_directory_binary) / Path(history_name_binary)
            except TypeError:
                return
        if self.should_have_mesastar1:
            log_directory_star1 = kwargs.get("log_directory_star1")
            history_name_star1 = kwargs.get("history_name_star1")
            try:
                fname_star1 = Path(self.run_directory) / Path(run_name) / Path(log_directory_star1) / Path(history_name_star1)
            except TypeError:
                return
        if self.should_have_mesastar2:
            log_directory_star2 = kwargs.get("log_directory_star2")
            history_name_star2 = kwargs.get("history_name_star2")
            try:
                fname_star2 = Path(self.run_directory) / Path(run_name) / Path(log_directory_star2) / Path(history_name_star2)
            except TypeError:
                return

        self._MESAbinaryHistory = None
        self._MESAstar1History = None
        self._MESAstar2History = None

        # load MESAbinary stuff
        if self.should_have_mesabinary:
            self._MESAbinaryHistory = MESAbinary(history_name=str(fname_binary))
        if self.should_have_mesastar1:
            self._MESAstar1History = MESAstar(history_name=str(fname_star1))
        if self.should_have_mesastar2:
            self._MESAstar2History = MESAstar(history_name=str(fname_star2))

        if self._MESAbinaryHistory is not None:
            self.have_mesabinary = True
        if self._MESAstar1History is not None:
            self.have_mesastar1 = True
        if self._MESAstar2History is not None:
            self.have_mesastar2 = True

    def get_initial_conditions(self) -> None:
        """Load initial conditions from MESAbinary & MESAstar output"""

        self.initial_conditions = dict()

        if self.have_mesabinary:
            self.initial_conditions["binary"] = self._MESAbinaryHistory.initial_conditions()

        if self.have_mesastar1:
            self.initial_conditions["star1"] = self._MESAstar1History.initial_conditions()

        if self.have_mesastar2:
            self.initial_conditions["star2"] = self._MESAstar2History.initial_conditions()
