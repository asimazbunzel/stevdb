"""Module driver to make a summary of a MESA simulation"""

from collections import OrderedDict
from pathlib import Path
from typing import Union
import sys

import numpy as np
from scipy.interpolate import interp1d

from stevdb.io import logger
from stevdb.mesa.mesa import MESAdata
from stevdb.mesa.spectypes import find_besttype
from stevdb.mesa.utils import (
    clight,
    eta,
    group_consecutives,
    Lsun,
    Msun,
    P_to_a,
    Rsun,
    R_NS,
    secyer,
    standard_cgrav,
)


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

    LOG_MT_MIN_LIMIT = -10e0
    H_THRESHOLD = 1e-5
    HE_THRESHOLD = 1e-5
    MAX_NS_MASS = 2e0

    LX_THRESHOLD = 1e30

    LOGG_SUN = 4.4380676273031332

    def __init__(
        self,
        template_directory: Union[str, Path] = "",
        run_directory: Union[str, Path] = "",
        run_name: str = "",
        is_binary_evolution: bool = True,
        **kwargs,
    ) -> None:

        # let folders be handled by pathlib module
        if isinstance(template_directory, str):
            self.template_directory = Path(template_directory)
        else:
            self.template_directory = template_directory

        if isinstance(run_directory, str):
            self.run_directory = Path(run_directory)
        else:
            self.run_directory = run_directory

        self.is_binary_evolution = is_binary_evolution

        self.run_name = run_name

        # possible kwargs for a MESA run
        run_args = {
            "explore_kicks": False,
            "natal_kicks_name": "",
            "primary_star_folder_name": "LOGS1",
            "secondary_star_folder_name": "LOGS2",
            "binary_folder_name": "LOGS_binary",
            "primary_star_history_name": "history.data",
            "secondary_star_history_name": "history.data",
            "binary_history_name": "binary_history.data",
            "star_folder_name": "LOGS",
            "star_history_name": "history.data",
            "core_collapse_folder_name": "cc_data",
            "star_at_core_collapse_name": "star_at_core_collapse.data",
            "binary_at_core_collapse_name": "binary_at_core_collapse.data",
            "termination_code_folder_name": "termination_codes",
            "termination_code_name": "termination_code_star_plus_point_mass",
        }

        for key, value in kwargs.items():
            if key in run_args:
                run_args[key] = value
            else:
                logger.error(
                    f"warning: unrecognized keyword argument: `{key}`. will ignore it"
                )

        self.run_args = run_args

        # MESA logs
        self.have_star_log = False
        self.have_binary_log = False
        self.have_primary_log = False
        self.have_secondary_log = False
        self.__star_log__ = None
        self.__primary_log__ = None
        self.__secondary_log__ = None
        self.__binary_log__ = None

        # compact companion type
        self.is_BH = False
        self.is_NS = False

        # summary output is stored in this dictionary
        self.summary_dict = dict()

        # load MESA output once at start
        logger.info("loading MESA logs")
        if self.is_binary_evolution:

            logger.info("- primary star")
            try:
                primary_name = str(
                    self.run_directory
                    / self.run_name
                    / f"{self.run_args.get('primary_star_folder_name')}"
                    / f"{self.run_args.get('primary_star_history_name')}"
                )
                self.__primary_log__ = self._load_output(fname=primary_name)
                self.have_primary_log = True
            except Exception as e:
                logger.error(str(e))

            logger.info("- secondary star")
            try:
                secondary_name = str(
                    self.run_directory
                    / self.run_name
                    / f"{self.run_args.get('secondary_star_folder_name')}"
                    / f"{self.run_args.get('secondary_star_history_name')}"
                )
                self.__secondary_log__ = self._load_output(fname=secondary_name)
                self.have_secondary_log = True
            except Exception as e:
                logger.error("NESA output for secondary star not found. not using it")

            logger.info("- binary")
            try:
                binary_name = str(
                    self.run_directory
                    / self.run_name
                    / f"{self.run_args.get('binary_folder_name')}"
                    / f"{self.run_args.get('binary_history_name')}"
                )
                self.__binary_log__ = self._load_output(fname=binary_name)
                self.have_binary_log = True
            except Exception as e:
                logger.error(str(e))

        else:
            print("not ready to use")
            sys.exit(1)

    def _load_output(self, fname: Union[str, Path] = "") -> None:
        """Load MESA output

        Parameters
        ----------
        fname : `str / Path`
            Name of the file with the MESA output
        """

        return MESAdata(fname, compress=False)

    def _get_value_from_core_collapse_file(
        self, fname: Union[str, Path] = "", string: str = ""
    ) -> None:
        """Return a value from a file

        Parameters
        ----------
        fname : `str / Path`
            Name of the file

        string : `str`
            Matching string in file
        """

        with open(fname, "r") as f:
            lines = f.readlines()

        value = None
        for line in lines:
            if string in line:
                value = line.strip().split()[1]

        if value is None:
            print(f"cannot find `{string}` in {fname}")
            sys.exit(1)

        return value if string == "sn_model" else float(value)

    def get_initial_conditions(self) -> None:
        """Get initial conditions of the MESArun"""

        logger.debug("getting initial conditions of the MESArun")

        if self.is_binary_evolution:
            if self.have_binary_log:
                try:
                    self.summary_dict["m1i"] = self.__binary_log__.data.get(
                        "star_1_mass"
                    )[0]
                except TypeError:
                    self.summary_dict["m1i"] = self.__binary_log__.get("star_1_mass")

                try:
                    self.summary_dict["m2i"] = self.__binary_log__.data.get(
                        "star_2_mass"
                    )[0]
                except TypeError:
                    self.summary_dict["m2i"] = self.__binary_log__.get("star_2_mass")

                try:
                    self.summary_dict["porbi"] = self.__binary_log__.data.get(
                        "period_days"
                    )[0]
                except TypeError:
                    self.summary_dict["porbi"] = self.__binary_log__.get("period_days")

                self.summary_dict["ai"] = P_to_a(
                    period=self.summary_dict["porbi"],
                    m1=self.summary_dict["m1i"],
                    m2=self.summary_dict["m2i"],
                )

                try:
                    self.summary_dict["ecci"] = self.__binary_log__.data.get(
                        "eccentricity"
                    )[0]
                except TypeError:
                    self.summary_dict["ecci"] = self.__binary_log__.get("eccentricity")

                # find out if the simulation contains a NS or a BH as compact object
                if self.summary_dict["m2i"] > self.MAX_NS_MASS:
                    self.is_BH = True
                else:
                    self.is_NS = True

        else:
            print("not ready to use")
            sys.exit(1)

    def get_termination_condition(self) -> None:
        """Find out how the simulation ended"""

        logger.debug("searching for termination condition")

        fname = str(
            self.run_directory
            / self.run_name
            / f"{self.run_args.get('termination_code_folder_name')}"
            / f"{self.run_args.get('termination_code_name')}"
        )

        if not Path(fname).is_file():
            code = None

        else:
            with open(fname, "r") as f:
                code = f.readline().strip("\n")

        if code is None:
            code = "None"

        # this patch is to be careful about what we call white-dwarf
        if code == "white-dwarf":
            code = "WD/NS"

        self.summary_dict["termination_code"] = code

    def get_pre_collapse_conditions(self) -> None:
        """Get conditions at the end of the evolution assuming core-collapse"""

        logger.debug("getting info just before core collapse")

        # everything will be stored here
        self.summary_dict["core_collapse"] = dict()

        # name of the file with the core-collapse info
        cc_star_fname = str(
            self.run_directory
            / self.run_name
            / self.run_args.get("core_collapse_folder_name")
            / self.run_args.get("star_at_core_collapse_name")
        )
        cc_binary_fname = str(
            self.run_directory
            / self.run_name
            / self.run_args.get("core_collapse_folder_name")
            / self.run_args.get("binary_at_core_collapse_name")
        )

        # info pre-cc to get from file
        names_star = (
            "he_core_mass_pre_cc",
            "c_core_mass_pre_cc",
            "radius_pre_cc",
            "Teff_pre_cc",
            "L_pre_cc",
        )
        names_binary = (
            "orbital_angular_momentum_pre_cc",
            "period_pre_cc",
            "separation_pre_cc",
            "r_1_pre_cc",
            "r_2_pre_cc",
            "rl_1_pre_cc",
            "rl_2_pre_cc",
            "mt_rate_pre_cc",
        )

        # set defaults in case there is no core-collapse
        if not "core-collapse" in self.summary_dict["termination_code"]:
            for name in names_star:
                self.summary_dict["core_collapse"][name] = None
            for name in names_binary:
                self.summary_dict["core_collapse"][name] = None

        else:
            for name in names_star:
                self.summary_dict["core_collapse"][
                    name
                ] = self._get_value_from_core_collapse_file(
                    fname=cc_star_fname, string=name
                )
            for name in names_binary:
                self.summary_dict["core_collapse"][
                    name
                ] = self._get_value_from_core_collapse_file(
                    fname=cc_binary_fname, string=name
                )

    def get_collapse_conditions(self) -> None:
        """Get conditions at core-collapse and the outcome of it"""

        logger.debug("getting info at core collapse")

        # check that dict exists !
        if "core_collapse" not in self.summary_dict.keys():
            self.summary_dict["core_collapse"] = dict()

        # info at cc from file
        names = ("sn_model", "ejected_mass", "fallback_mass", "remnant_mass")

        # name of the file with the core-collapse info
        cc_star_fname = str(
            self.run_directory
            / self.run_name
            / self.run_args.get("core_collapse_folder_name")
            / self.run_args.get("star_at_core_collapse_name")
        )

        # set defaults in case there is no core-collapse
        if not "core-collapse" in self.summary_dict["termination_code"]:
            for name in names:
                self.summary_dict["core_collapse"][name] = None

        else:
            for name in names:
                self.summary_dict["core_collapse"][
                    name
                ] = self._get_value_from_core_collapse_file(
                    fname=cc_star_fname, string=name
                )

    def get_xrb_phase_conditions(self) -> None:
        """Search for XRB phase(s) during the evolution of star + compact object"""

        logger.debug("searching for XRB phase(s)")

        # set defaults here
        self.summary_dict["xrb_phase"] = None
        self.summary_dict["is_xrb"] = False

        if self.is_binary_evolution:
            if self.have_binary_log:
                # need this
                rl_rel_overflow1 = self._compute_relative_rlof()
                lg_mtransfer_rate = self.__binary_log__.get("lg_mtransfer_rate")
                model_numbers = self.__binary_log__.get("model_number").astype(int)
                model_numbers = np.arange(len(model_numbers))

                # definition of XRB
                #  mt_rlof = (rl_rel_overflow1 > 0) & (
                    #  lg_mtransfer_rate > self.LOG_MT_MIN_LIMIT
                #  )
                #  mt_wind = (rl_rel_overflow1 < 0) & (
                    #  lg_mtransfer_rate > self.LOG_MT_MIN_LIMIT
                #  )

                # definition of XRB: X-ray luminosity above a threshold
                lg_lxs = self._compute_xray_luminosity(model_numbers=model_numbers)
                lx = np.power(10, lg_lxs[0]) + np.power(10, lg_lxs[1]) > self.LX_THRESHOLD

                # if there are models fulfilling this condition, we have a XRB
                # if any(mt_rlof) or any(mt_wind):
                if any(lx):
                    logger.debug("XRB phase(s) found")

                    # things will be stored in this dict
                    self.summary_dict["xrb_phase"] = dict()

                    model_numbers_as_xrb = group_consecutives(
                        vals=self.__binary_log__.get("model_number")[lx]
                    )

                    # each XRB phase is treated separately
                    for k in range(len(model_numbers_as_xrb)):

                        # sometimes we need to remove one index in the list because fortran starts counting with 1 and python with 0
                        mod_num = model_numbers_as_xrb[k][:-2]

                        # remove cases with only one model as XRB
                        if len(self.__binary_log__.get("model_number")[mod_num]) <= 1:
                            logger.debug(
                                f"id {k}: only one model as XRB is not a proper XRB candidate"
                            )
                            continue
                        else:
                            self.summary_dict["xrb_phase"][k] = dict()
                            self.summary_dict["is_xrb"] = True

                        # find out type of MT
                        self.summary_dict["xrb_phase"][k][
                            "mt_type"
                        ] = self._find_type_of_mass_transfer(model_numbers=mod_num)
                        self.summary_dict["xrb_phase"][k][
                            "mt_case"
                        ] = self._find_case_of_mass_transfer(model_numbers=mod_num)

                        # timestep
                        if self.have_primary_log:
                            self.summary_dict["xrb_phase"][k]["timestep"] = np.power(
                                10, self.__primary_log__.get("log_dt")[mod_num]
                            )
                            self.summary_dict["xrb_phase"][k][
                                "spectral_type"
                            ] = self._set_spectral_type_of_donor(
                                model_numbers=mod_num,
                                log_Teff=self.__primary_log__.get("log_Teff")[mod_num],
                                log_g=self.__primary_log__.get("log_g")[mod_num],
                            )
                        else:
                            logger.critical(
                                "does not have a primary star in a binary system !"
                            )
                            sys.exit(1)

                        if self.have_binary_log:
                            self.summary_dict["xrb_phase"][k][
                                "porb"
                            ] = self.__binary_log__.get("period_days")[mod_num]
                            self.summary_dict["xrb_phase"][k][
                                "ecc"
                            ] = self.__binary_log__.get("eccentricity")[mod_num]
                            self.summary_dict["xrb_phase"][k][
                                "lg_mdot_rlof"
                            ] = self.__binary_log__.get("lg_mtransfer_rate")[mod_num]
                            self.summary_dict["xrb_phase"][k][
                                "lg_mdot_wind"
                            ] = self.__binary_log__.get("lg_wind_mdot_1")[mod_num]
                            self.summary_dict["xrb_phase"][k][
                                "rl_rel_overflow"
                            ] = self._compute_relative_rlof()[mod_num]
                            (
                                self.summary_dict["xrb_phase"][k]["lx_rlof"],
                                self.summary_dict["xrb_phase"][k]["lx_wind"],
                            ) = self._compute_xray_luminosity(model_numbers=mod_num)

                            # check that dimensions are OK
                            n_test = len(self.summary_dict["xrb_phase"][k]["ecc"])
                            for name in (
                                "porb",
                                "ecc",
                                "lg_mdot_rlof",
                                "lg_mdot_wind",
                                "rl_rel_overflow",
                                "lx_rlof",
                                "lx_wind",
                            ):
                                n = len(self.summary_dict["xrb_phase"][k][name])
                                if n != n_test:
                                    logger.critical(
                                        f"dimensions not matching for item `{name}`"
                                    )

    def _compute_relative_rlof(self):
        """Compute the relative RLOF for a star"""

        # need this
        eccentricity = self.__binary_log__.get("eccentricity")
        R1 = self.__binary_log__.get("star_1_radius")
        RL1 = self.__binary_log__.get("rl_1")

        return (R1 - RL1 * (1 - eccentricity)) / (RL1 * (1 - eccentricity))

    def _find_type_of_mass_transfer(self, model_numbers: list = []) -> str:
        """Find out which type of MT phase happened. Output will be: `wind`, `rlof`, `both`, `none`

        Parameters
        ----------
        model_numbers : `list`
            Array with model numbers

        Returns
        -------
        mt_type : `str`
            String with the type of MT phase
        """

        # useful stuff
        star_relative_overflow = self._compute_relative_rlof()[model_numbers]
        lg_mtransfer_rate = self.__binary_log__.get("lg_mtransfer_rate")[model_numbers]

        # flags for finding MT types
        is_rlof = False
        is_wind = False

        # mask on rlof
        mask_rlof = (star_relative_overflow > 0) & (lg_mtransfer_rate > self.LOG_MT_MIN_LIMIT)
        if any(mask_rlof):
            is_rlof = True

        # mask on winds
        mask_winds = (star_relative_overflow < 0) & (lg_mtransfer_rate > self.LOG_MT_MIN_LIMIT)
        if any(mask_winds):
            is_wind = True

        if is_rlof and is_wind:
            mt_type = "both"
        elif is_rlof:
            mt_type = "rlof"
        elif is_wind:
            mt_type = "wind"
        else:
            mt_type = "none"

        return mt_type

    def _find_case_of_mass_transfer(self, model_numbers: list = []) -> str:
        """Find out which case of MT phase it is, as definede by Kippenhahn & Weigert (1967)

        Possible outputs are: `a`, `b`,`c`

        Parameters
        ----------
        model_numbers : `list`
            Array with model numbers

        Returns
        -------
        mt_case : `str`
        self.
            String with the case of MT phase
        """

        # useful stuff
        if self.have_primary_log:
            center_h1 = self.__primary_log__.get("center_h1")
            center_he4 = self.__primary_log__.get("center_he4")

        elif self.have_star_log:
            center_h1 = self.__star_log__.get("center_h1")
            center_he4 = self.__star_log__.get("center_he4")

        k0 = model_numbers[0]

        if center_h1[k0] > self.H_THRESHOLD:
            mt_case = "A"

        elif center_he4[k0] > self.HE_THRESHOLD:
            mt_case = "B"

        else:
            mt_case = "C"

        return mt_case

    def _set_spectral_type_of_donor(
        self, model_numbers: list = [], log_Teff: list = [], log_g: list = [],
    ) -> list:
        """Define a spectral type for the donor star

        Parameters
        ----------
        model_numbers : `list`
            Array with model numbers

        log_Teff : `list`
            Array with effective temperatures

        Returns
        -------
        spectral_type : `list`
            List of strings with the spectral type of the non-degenerate donor star
        """

        sp_type = []
        for k in range(len(model_numbers)):
            kTeff = np.power(10, log_Teff[k]) / 1e3
            logg_gsun = log_g[k] - self.LOGG_SUN

            sptypes = find_besttype(Teff=kTeff, logg=logg_gsun)

            if abs(float(sptypes[0][1]) - float(sptypes[1][1])) < 1e-3:
                logger.debug(
                    f"undefined spectral clasiffication for index k={k}: {sptypes[0]} or "
                    f"{sptypes[1]}. using first one"
                )

            sp_type.append(sptypes[0][0])

        return np.array(sp_type)

    def _compute_mdot_edd(self, mass):
        """Eddington mass loss rate for a compact accretor"""

        mdot_edd = 2.6e-7 * (mass / 10e0) * (eta / 0.1)

        return mdot_edd * Msun / secyer

    def _compute_xray_luminosity(self, model_numbers: list = []) -> list:
        """Compute the X-ray luminosity due to accretion

        Parameters
        ----------
        model_numbers : `list`
            Array with model numbers

        Returns
        -------
        lx_rlof : `list`
            X-ray luminosity due to RLOF

        lx_wind : `list`
            X-ray luminosity due to winds
        """

        def beta_w(m):
            """Linear interpolation for beta value as in Belczynski+ 2008

            Parameters
            ----------
            m : `list`
                List of masses where we are interpolating to get the beta value of the wind

            Returns
            -------
            f(m) : `list`
                Interpolated beta values for masses m
            """

            # below and above limits, replace values
            m = np.where(m < 1.4, 1.4, m)
            m = np.where(m > 120, 120, m)

            masses = [1.4, 120]
            betas = [0.125, 7]
            f = interp1d(masses, betas)

            return f(m)

        # for testing purposes
        test = False

        # need this, all in cgs units
        if self.have_binary_log:
            m1 = self.__binary_log__.get("star_1_mass")[model_numbers] * Msun
            m2 = self.__binary_log__.get("star_2_mass")[model_numbers] * Msun
            a = self.__binary_log__.get("binary_separation")[model_numbers] * Rsun
            e = self.__binary_log__.get("eccentricity")[model_numbers]
            wind1 = np.power(10, self.__binary_log__.get("lg_wind_mdot_1"))[
                model_numbers
            ] * Msun / secyer
            mtransfer_rate = np.power(10, self.__binary_log__.get("lg_mtransfer_rate"))[
                model_numbers
            ] * Msun / secyer
            eff_xfer_fraction = self.__binary_log__.get("eff_xfer_fraction")[
                model_numbers
            ]
            r1 = self.__binary_log__.get("star_1_radius")[model_numbers] * Rsun
            acc_lum_bh = np.power(10, self.__binary_log__.get("lg_accretion_luminosity"))[
                model_numbers
            ] * Lsun

        else:
            logger.critical("need binary log to compute xray luminosity")
            sys.exit(1)

        if test:
            m1 = np.array([29e0]) * Msun
            m2 = np.array([1.4]) * Msun
            a = P_to_a(np.array([164.6]), m1/Msun, m2/Msun) * Rsun
            e = np.array([0.8])
            r1 = np.array([40e0]) * Rsun
            wind1 = np.array([np.power(10, -5.7)]) * Msun / secyer
            mtransfer_rate = np.array([0])
            eff_xfer_fraction = np.array([1])
            acc_lum_bh = np.array([0e0])

        # luminosity due to RLOF
        if self.is_NS:
            mdot_rlof = mtransfer_rate * eff_xfer_fraction
            lx_rlof = eta * standard_cgrav * m2 * mdot_rlof / R_NS  # erg/s

        else:
            lx_rlof = acc_lum_bh

        # velocities: orbital and winds
        v_orb = np.sqrt(standard_cgrav * m1 / a)
        v_wind = np.sqrt(2 * beta_w(m1 / Msun)  * standard_cgrav * m1 / r1)

        wind_xfer = 1.5e0 / (2 * np.power(a, 2)) / np.sqrt(1 - np.power(e, 2))
        wind_xfer *= np.power(standard_cgrav * m2 / (v_wind * v_wind), 2)
        wind_xfer *= np.power((1 + np.power(v_orb / v_wind, 2)), -1.5e0)
        wind_xfer = np.where(wind_xfer > 1, 1, wind_xfer)

        # mass accreted through winds
        mdot_wind = wind_xfer * wind1  # in g s^-1

        # limit accretion to be less than mass lost by donor or due to eddington limit
        mdot_wind = np.where(
            mdot_wind > self._compute_mdot_edd(m2/Msun),
            self._compute_mdot_edd(m2/Msun),
            mdot_wind
        )
        mdot_wind = np.where(
            mdot_wind > 0.5 * wind1,
            0.5 * wind1,
            mdot_wind
        )

        # accretion luminosity in Bondi-Hoyle mechanism
        if self.is_NS:
            lx_wind = eta * standard_cgrav * m2 * Msun * mdot_wind / R_NS  # erg/s

        else:
            lx_wind = eta * mdot_wind * clight**2

        return np.log10(lx_rlof), np.log10(lx_wind)

    def ordered_dict(self):
        """Make an ordered dictionary of information for the stellar evolution model"""

        return OrderedDict(
            (key, getattr(self, key))
            for key in (
                "run_name",
                "template_directory",
                "run_directory",
                "is_binary_evolution",
                "summary_dict",
            )
        )
