"""Module with class to load MESA output"""

from pathlib import Path
from typing import Union

import numpy as np

from ..io.logger import logger
from .mappings import map_termination_code
from .utils import MESAdata
from .utils import P_to_a
from .utils import group_consecutives


class MESAstar(object):
    """Class to handle MESAstar output

    Naming convention follows MESA defaults
    """

    def __init__(self, history_name: Union[str, Path] = "", termination_name: Union[str, Path] = "", mesa_dir: str = "") -> None:

        logger.debug("load MESAstar output")

        self.history_name = history_name
        self.termination_name = termination_name
        self.mesa_dir = mesa_dir

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

        code = map_termination_code(mesa_dir=self.mesa_dir, termination_code=code)

        return code


class MESAbinary(object):
    """Class to handle MESAbinary output

    Naming convention follows MESA defaults
    """

    def __init__(self, history_name: Union[str, Path] = "", termination_name: Union[str, Path] = "", mesa_dir: str = "") -> None:

        logger.debug("load MESAbinary output")

        self.history_name = history_name
        self.termination_name = termination_name
        self.mesa_dir = mesa_dir

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

        code = map_termination_code(mesa_dir=self.mesa_dir, termination_code=code)

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
            rl_relative_overflow_1 = self._compute_relative_rlof(star_id=1)
        except KeyError:
            return xrbPhase

        lg_mtransfer_rate = self.History.get("lg_mtransfer_rate")
        model_number = self.History.get("model_number").astype(int)
        model_number = np.arange(len(model_number))

        # definition of XRB: X-ray luminosity above a threshold
        lg_lxs = self._compute_xray_luminosity(model_number=model_number)
        lx = np.power(10, lg_lxs[0]) + np.power(10, lg_lxs[1]) > self.LX_THRESHOLD

        # if there are models fulfilling this condition, we have a XRB
        if any(lx):

            logger.debug("XRB phase(s) found")

            model_number_as_xrb = group_consecutives(vals=self.History.get("model_number")[lx])

        return xrbPhase
