"""Module with class to load MESA output"""

from pathlib import Path
from typing import Union

from ..io.logger import logger
from .utils import MESAdata
from .utils import P_to_a

codesMap = {
    "ce merge": "CE merge",
    "max_model_number": "numerical issue (max model number)",
    "min_timestep_limit": "numerical issue (small timestep)",
    "white-dwarf": "WD/NS",
}


class MESAstar(object):
    """Class to handle MESAstar output

    Naming convention follows MESA defaults
    """

    def __init__(self, history_name: Union[str, Path] = "", termination_name: Union[str, Path] = "") -> None:

        logger.debug("load MESAstar output")

        self.history_name = history_name
        self.termination_name = termination_name

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

    def termination_condition(self) -> str:
        """Find out how the simulation ended"""

        logger.debug("searching for termination condition")

        if not Path(self.termination_name).is_file():
            code = None
        else:
            with open(self.termination_name, "r") as f:
                code = f.readline().strip("\n")

        if code is None:
            code = "None"

        if code in codesMap:
            code = codesMap[code]

        return code


class MESAbinary(object):
    """Class to handle MESAbinary output

    Naming convention follows MESA defaults
    """

    def __init__(self, history_name: Union[str, Path] = "", termination_name: Union[str, Path] = "") -> None:

        logger.debug("load MESAbinary output")

        self.history_name = history_name
        self.termination_name = termination_name

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
        initial_conditions["initial_separation_in_Rsuns"] = P_to_a(
            period=initial_conditions["initial_period_in_days"], m1=initial_conditions["m1"], m2=initial_conditions["m2"]
        )

        return initial_conditions

    def termination_condition(self) -> str:
        """Find out how the simulation ended"""

        logger.debug("searching for termination condition")

        if not Path(self.termination_name).is_file():
            code = None
        else:
            with open(self.termination_name, "r") as f:
                code = f.readline().strip("\n")

        if code is None:
            code = "None"

        if code in codesMap:
            code = codesMap[code]

        return code

    def _compute_relative_rlof(self, star_id: int = -1):
        """Compute relative RLOF as: (R - RL) / RL"""

        try:
            ecc = self.History.get("eccentricitiy")
        except KeyError:
            raise KeyError("`eccentricity` not found")

        if star_id == 1:
            R = self.History.get("star_1_radius")
            RL = self.History.get("rl_1")
        elif star_id == 2:
            R = self.History.get("star_2_radius")
            RL = self.History.get("rl_2")

        return (R - RL * (1 - ecc)) / (RL * (1 - ecc))

    def xrb_phase(self) -> dict:
        """Values during XRB phase"""

        xrbPhase = dict()

        try:
            self._compute_relative_rlof(star_id=1)
        except KeyError:
            return xrbPhase
