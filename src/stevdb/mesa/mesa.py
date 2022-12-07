"""Module with class to load MESA output"""

from pathlib import Path
from typing import Union

from ..io.logger import logger
from .utils import MESAdata, P_to_a

class MESAstar(object):
    """Class to handle MESAstar output

    Naming convention follows MESA defaults
    """

    def __init__(self, history_name: Union[str, Path] = "") -> None:

        logger.debug("load MESAstar output")

        self.history_name = history_name

        try:
            self.History = MESAdata(fname=self.history_name, compress=False)
        except FileNotFoundError:
            self.History = None

    def initial_conditions(self) -> dict:
        """Search for initial conditions of MESAstar output"""

        initial_conditions = dict()

        try:
            initial_conditions["initial_mass"] = self.History.get("star_mass")[0]
        except Exception:
            initial_conditions["initial_mass"] = self.History.get("star_mass")

        return initial_conditions


class MESAbinary(object):
    """Class to handle MESAbinary output

    Naming convention follows MESA defaults
    """

    def __init__(self, history_name: Union[str, Path] = "") -> None:

        logger.debug("load MESAbinary output")

        self.history_name = history_name

        try:
            self.History = MESAdata(fname=self.history_name, compress=False)
        except FileNotFoundError:
            self.History = None

    def initial_conditions(self) -> dict:
        """Search for initial conditions of MESAbinary output"""

        initial_conditions = dict()

        try:
            initial_conditions["m1"] = self.History.get("star_1_mass")[0]
        except Exception:
            initial_conditions["m1"] = self.History.get("star_1_mass")

        try:
            initial_conditions["m2"] = self.History.get("star_2_mass")[0]
        except Exception:
            initial_conditions["m2"] = self.History.get("star_2_mass")

        try:
            initial_conditions["initial_period_in_days"] = self.History.get("period_days")[0]
        except Exception:
            initial_conditions["initial_period_in_days"] = self.History.get("period_days")

        try:
            initial_conditions["initial_eccentricity"] = self.History.get("eccentricity")[0]
        except Exception:
            initial_conditions["initial_eccentricity"] = self.History.get("eccentricity")

        # separation is computed using Kepler law
        initial_conditions["initial_separation_in_Rsuns"] = P_to_a(period=initial_conditions["initial_period_in_days"], m1=initial_conditions["m1"], m2=initial_conditions["m2"])

        return initial_conditions
