"""
Database module
"""


import sqlite3
from collections import OrderedDict

import numpy as np

from .logger import logger


def create_database(database_filename: str = "", table_name: str = "", table_dict: OrderedDict = OrderedDict()) -> None:
    """Create table in database with the summary of the simulations

    Parameters
    ----------
    database_filename : `str`
        Name of the file with the database

    table_name : `str`
        Name of the table to be created

    table_dict : `dict`
        Dictionary with the information to be stored in the table of the database
    """

    logger.debug(f" creating database table {table_name}")

    # maps between python and sqlite
    dtype_map = {
        None: "NULL",
        int: "INTEGER",
        float: "REAL",
        np.float64: "REAL",
        str: "TEXT",
        bytes: "BLOB",
        bool: "INTEGER",
    }

    # create database
    conn = sqlite3.connect(database_filename)

    # connect to it with a cursor
    c = conn.cursor()

    cmd = f"CREATE TABLE IF NOT EXISTS {table_name} ("

    # table_dict contains keys for either a star (star1 and/or star2) as well as the binary
    # in order to produce a single table, we construct a new dictionary combining the other two
    # but changing the keys in the star* dicts in order to contain an identificator to the star
    # to which it corresponds
    for key, value in table_dict.items():
        cmd += f"{key} {dtype_map[type(value)]}, "

    # wrap up command with the final parenthesis
    cmd = cmd[:-2]
    cmd += ");"

    # create table
    c.execute(cmd)

    # commit changes
    conn.commit()

    # close connection
    conn.close()


def insert_run_into_database(database_filename: str = "", table_name: str = "", table_dict: OrderedDict = OrderedDict()) -> None:
    """Insert record into a database

    Parameters
    ----------
    database_filename : `str`
        Name of the file with the database

    table_name : `str`
        Name of the table to be created

    table_dict : `dict`
        Dictionary with the information to be stored in the table of the database
    """

    # create database
    conn = sqlite3.connect(database_filename)

    # connect to it with a cursor
    c = conn.cursor()

    cmd = f"INSERT INTO {table_name}"
    cmd_column_names = "("
    cmd_column_values = "("

    # append row depending on the type of the value
    for key, value in table_dict.items():
        if isinstance(value, str):
            cmd_column_names += f"{key}, "
            cmd_column_values += f"'{value}', "
        else:
            cmd_column_names += f"{key}, "
            cmd_column_values += f"{value}, "

    # write row to MESArun database
    cmd = f"{cmd} {cmd_column_names[:-2]}) VALUES {cmd_column_values[:-2]})"

    # append record to table
    c.execute(cmd)

    # commit changes
    conn.commit()

    # close connection
    conn.close()
