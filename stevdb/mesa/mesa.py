"""Module with class to load MESA output"""

import gzip
from pathlib import Path
import subprocess
from typing import Union

import numpy as np


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
            header_names = [
                name.decode("utf8") for name in file.readline().strip().split()
            ]
        else:
            header_names = file.readline().strip().split()

        # After that are header names values
        if is_gz:
            header_values = [
                val.decode("utf8") for val in file.readline().strip().split()
            ]
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
            for i in range(len(model_number) - 2, -1, -1):
                if int(model_number[i]) >= last_model:
                    mask[i] = 1
                else:
                    last_model = int(model_number[i])

            for name in col_names:
                self.data[name] = np.ma.masked_array(
                    self.data[name], mask=mask
                ).compressed()

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
        arg (str): column name

        Returns
        -------
        a: array of elements corresponding to the column name given
        """
        return self.data[arg]
