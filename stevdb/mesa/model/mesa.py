"""Module with class to load MESA output"""

from typing import Union

import gzip
import subprocess
from pathlib import Path

import numpy as np

from .mappings import map_termination_code


class AttributeMapper:
    """Map to access dictionary items as attributes

    Idea from pandas DataFrame obj
    """

    def __init__(self, obj) -> None:  # type: ignore
        self.__dict__["data"] = obj

    def __getattr__(self, attr):
        if attr in self.data:
            found_attr = self.data[attr]
            if isinstance(found_attr, dict):
                return AttributeMapper(found_attr)
            else:
                return found_attr
        else:
            raise AttributeError

    def __setattr__(self, attr, value):
        if attr in self.data:
            self.data[attr] = value
        else:
            raise NotImplementedError

    def __dir__(self):
        return self.data.keys()


class NoSingleValueFoundException(Exception):
    pass


class MESAdata:
    """Class with the output a MESA simulation

    Parameters
    ----------
    fname : `str`
        Name of the file with the MESA output
    compress : `bool`
        Flag to check if we want to compress output after loading it
    """

    def __init__(
        self,
        history_name: Union[str, Path] = "",
        termination_name: Union[str, Path] = "",
        core_collapse_name: Union[str, Path] = "",
        mesa_dir: str = "",
        compress: bool = False,
    ) -> None:

        # always use pathlib
        if isinstance(history_name, str):
            fname_tmp = Path(history_name)
        else:
            fname_tmp = history_name

        # check for fname, or fname.gz for compressed data
        is_gz: bool
        if fname_tmp.is_file():
            is_gz = False
        else:
            # try with a gzip version of the same name
            gz_fname = Path(f"{history_name}.gz")
            if gz_fname.is_file() is False:
                raise FileNotFoundError
            else:
                is_gz = True

        self.history_name = history_name
        self.compress = compress
        # always use pathlib
        if isinstance(core_collapse_name, str):
            self.core_collapse_name = Path(core_collapse_name)
        else:
            self.core_collapse_name = core_collapse_name
        if isinstance(termination_name, str):
            self.termination_name = Path(termination_name)
        else:
            self.termination_name = termination_name
        self.mesa_dir = mesa_dir
        self.header = dict()
        self.data = dict()
        self.data_cc = dict()

        # get termination code
        self.termination_code: str = self.termination_condition()

        # also, look for a file which has the information of the collapsing core
        # this is only possible for stars reaching core-collapse
        self.reaches_core_collapse: bool = self.has_core_collapse_file()

        # flag to check if it is a history file or not, based on the name of the file
        is_history = False
        if "history" in str(self.history_name):
            is_history = True

        # try to open file
        if is_gz:
            file = gzip.open(gz_fname, "rb")
        else:
            file = open(self.history_name)  # type: ignore

        # First line is not used
        file.readline()

        # Header names
        if is_gz:
            header_names = [name.decode("utf8") for name in file.readline().strip().split()]
        else:
            header_names = file.readline().strip().split()  # type: ignore

        # After that are header names values
        if is_gz:
            header_values = [val.decode("utf8") for val in file.readline().strip().split()]
        else:
            header_values = [val for val in file.readline().strip().split()]  # type: ignore

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
            col_names = file.readline().strip().split()  # type: ignore

        # close file
        file.close()

        # Arrays are loaded using numpy an treated them as np.arrays
        file_data = np.loadtxt(self.history_name, skiprows=6, unpack=True)

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
                    f"gzip {self.history_name}",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                )
                stdout, stderr = p.communicate()
            except Exception:
                pass

        if self.reaches_core_collapse:
            with open(self.core_collapse_name) as f:
                for line in f:
                    line = line.strip()
                    name = line.split(" ")[0]
                    try:
                        value = float(line.split(" ")[-1])
                    except ValueError:
                        value = str(line.split(" ")[-1])  # type: ignore

                    self.data_cc[name] = value

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
        if arg in self.data:
            return self.data[arg]
        elif arg in self.data_cc:
            return self.data_cc[arg]
        else:
            raise KeyError(f"could not find `{arg}` in data nor in data_cc")

    def has_core_collapse_file(self) -> bool:
        """Find out if the simulation has reached core-collapse stage"""

        return self.core_collapse_name.is_file()

    def termination_condition(self) -> str:
        """Find out how the simulation ended"""

        if not self.termination_name.is_file():
            code = None
        else:
            with open(self.termination_name) as f:
                code = f.readline().strip("\n")

        if code is None:
            code = "None"

        code = map_termination_code(mesa_dir=self.mesa_dir, termination_code=code)

        return code
