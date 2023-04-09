"""Utility functions for MESA output
"""

from typing import Any, List, Union

import numpy as np

one_third = 1e0 / 3e0
standard_cgrav = 6.67428e-8  # gravitational constant (g^-1 cm^3 s^-2)
secyer = 3.1558149984e7  # seconds per year
clight = 2.99792458e10  # speed of light in vacuum (cm s^-1)
Msun = 1.9892e33  # solar mass (g)  <<< gravitational mass, not baryonic
Rsun = 6.9598e10  # solar radius (cm)
Lsun = 3.828e33  # solar luminosity (erg s^-1)
R_NS = 10e0 * 1e5  # radius of a NS in cm
eta = 0.1  # efficiency in converting gravitational to radiation energy of accretion


def P_to_a(
    period: Union[float, np.ndarray], m1: Union[float, np.ndarray], m2: Union[float, np.ndarray]  # type: ignore
) -> Any:
    """Binary separation from known period

    Parameters
    ----------
    P: `float / np.ndarray`
        Binary period in days
    M1: `float / np.ndarray`
        Mass of primary star in Msun
    M2: `float / np.ndarray`
        Mass of secondary star in Msun

    Returns
    -------
    a: `float / np.ndarray`
        Binary separation in Rsun
    """
    period = period * 24e0 * 3600e0  # in sec
    m1 = m1 * Msun
    m2 = m2 * Msun  # in g

    to_power = standard_cgrav * (m1 + m2) * (period / (2 * np.pi)) ** 2
    return np.power(to_power, one_third) / Rsun


def a_to_P(
    separation: Union[float, np.ndarray], m1: Union[float, np.ndarray], m2: Union[float, np.ndarray]  # type: ignore
) -> Any:
    """Period from known separation

    Parameters
    ----------
    a: `float / np.ndarray`
        Binary separation in Rsun
    M1: `float / np.ndarray`
        Mass of primary star in Msun
    M2: `float / np.ndarray`
        Mass of secondary star in Msun

    Returns
    -------
    P: `float / np.ndarray`
        Binary period in days
    """
    separation = separation * Rsun  # in cm
    m1 = m1 * Msun
    m2 = m2 * Msun  # in g

    period = np.power(
        separation * separation * separation / (standard_cgrav * (m1 + m2)), 1e0 / 2e0
    )
    period *= 2 * np.pi
    return period / (24e0 * 3600e0)


def group_consecutives(vals: List[int] = [], step: int = 1) -> List[int]:
    """Return list of consecutive lists of numbers from vals (number list)

    Parameters
    ----------
    vals : `array`
        List of integer values to sort as consecutives
    step : `int`
        The step defining consecutive numbers

    Returns
    -------
    result: `array`
        Array with sorted as consecutive numbers, each element in another array
    """
    run: List[int] = []
    result = [run]
    expect = None
    for v in vals:
        v = int(v)
        if (v == expect) or (expect is None):
            run.append(v)
        else:
            run = [v]  # type: ignore
            result.append(run)
        expect = v + step
    return run
