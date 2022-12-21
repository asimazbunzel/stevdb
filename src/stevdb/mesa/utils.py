"""Utility functions for MESA output"""

import gzip
import subprocess
from pathlib import Path
from typing import Union

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


def P_to_a(period, m1, m2):
    """Binary separation from known period

    Parameters
    ----------
    P: `float`
        Binary period in days
    M1: `float`
        Mass of primary star in Msun
    M2: `float`
        Mass of secondary star in Msun

    Returns
    -------
    a: `float`
        Binary separation in Rsun
    """
    period = period * 24e0 * 3600e0  # in sec
    m1 = m1 * Msun
    m2 = m2 * Msun  # in g

    tmp = standard_cgrav * (m1 + m2) * (period / (2 * np.pi)) ** 2
    return np.power(tmp, one_third) / Rsun


def a_to_P(separation, m1, m2):
    """Period from known separation

    Parameters
    ----------
    a: `float`
        Binary separation in Rsun
    M1: `float`
        Mass of primary star in Msun
    M2: `float`
        Mass of secondary star in Msun

    Returns
    -------
    P: `float`
        Binary period in days
    """
    separation = separation * Rsun  # in cm
    m1 = m1 * Msun
    m2 = m2 * Msun  # in g

    period = np.power(separation * separation * separation / (standard_cgrav * (m1 + m2)), 1e0 / 2e0)
    period *= 2 * np.pi
    return period / (24e0 * 3600e0)


def group_consecutives(vals, step=1):
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
    run = []
    result = [run]
    expect = None
    for v in vals:
        v = int(v)
        if (v == expect) or (expect is None):
            run.append(v)
        else:
            run = [v]
            result.append(run)
        expect = v + step
    return


class MESAdata(object):
    """Class with the output a MESA simulation

    Parameters
    ----------
    fname : `str`
        Name of the file with the MESA output
    compress : `bool`
        Flag to check if we want to compress output after loading it
    """

    def __init__(self, fname: Union[str, Path] = "", compress: bool = False) -> None:
        # check for fname, or fname.gz for compressed data
        fname_tmp = Path(fname)
        if fname_tmp.is_file():
            is_gz = False

        else:
            # try with a gzip version of the same name
            gz_fname = Path(f"{fname}.gz")
            if gz_fname.is_file() is False:
                raise FileNotFoundError

            else:
                is_gz = True

        self.fname = fname
        self.compress = compress
        self.header = dict()
        self.data = dict()

        # flag to check if it is a history file or not, based on the name of the file
        is_history = False
        if "history" in self.fname:
            is_history = True

        # try to open file
        if is_gz:
            file = gzip.open(gz_fname, "rb")
        else:
            file = open(self.fname, "r")

        # First line is not used
        file.readline()

        # Header names
        if is_gz:
            header_names = [name.decode("utf8") for name in file.readline().strip().split()]
        else:
            header_names = file.readline().strip().split()

        # After that are header names values
        if is_gz:
            header_values = [val.decode("utf8") for val in file.readline().strip().split()]
        else:
            header_values = [val for val in file.readline().strip().split()]

        for i, name in enumerate(header_names):
            self.header[name] = header_values[i]

        # After header there is a blank line followed by an unused line.
        file.readline()
        file.readline()

        # Next are the column names
        if is_gz:
            tmp_col_names = file.readline().strip().split()
            col_names = [name.decode("utf8") for name in tmp_col_names]

        else:
            col_names = file.readline().strip().split()

        # close file
        file.close()

        # Arrays are loaded using numpy an treated them as np.arrays
        file_data = np.loadtxt(self.fname, skiprows=6, unpack=True)

        # put arrays into dictionary
        for i, name in enumerate(col_names):
            self.data[name] = np.array(file_data[i])

        try:
            n = len(self.data["model_number"])
        except TypeError:
            is_history = False

        if is_history:
            #  clean up log history
            #  --------------------
            #  the way it works is simple. It starts from the last model
            #  number and checks if that number is not repeated in the
            #  line before. This is combined with a mask so that it has
            #  a 0 (= True) for the lines that are not repeated and a 1
            #  (= False) for the repeated ones
            #  after the mask is created, each array-type column is
            #  filtered with this mask using some numpy methods
            #  (numpy.ma.masked_array & compressed)
            model_number = self.data["model_number"]
            last_model = int(model_number[-1])
            mask = np.zeros(len(model_number))
            for i in range(n - 2, -1, -1):
                if int(model_number[i]) >= last_model:
                    mask[i] = 1
                else:
                    last_model = int(model_number[i])

            for name in col_names:
                self.data[name] = np.ma.masked_array(self.data[name], mask=mask).compressed()

        # try to compress if permitted
        if self.compress:
            try:
                p = subprocess.Popen(
                    "gzip {}".format(self.fname),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                )
                stdout, stderr = p.communicate()
            except Exception:
                pass

    def get(self, arg):
        """
        Given a column name, it returns its values.

        Parameters
        -----------
        arg: `str`
            Column name

        Returns
        -------
        a: `list`
            Array of elements corresponding to the column name given
        """
        return self.data[arg]
