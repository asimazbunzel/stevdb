"""
Database module
"""

import sqlite3
import time
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

    logger.debug(f" creating database table: {table_name}")

    # (tstart) for timing db creation
    tstart = time.time()

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
        # sometimes, None values are passed (tipically with Final values). this is an ugly
        # path to avoid errors; # TODO: improve on this
        if value is None:
            cmd += f"{key} REAL, "
        else:
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

    # (tend) timing of db creation
    tend = time.time()
    logger.debug(f" [database creation time: {tend-tstart:.2f} sec]")


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

    logger.debug(f" inserting record into database table: {table_name}")

    # (tstart) for timing db data insertion
    tstart = time.time()

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

    # (tend) timing of db data insertion
    tend = time.time()
    logger.debug(f" [database record insertion time: {tend-tstart:.2f} sec]")


def load_database(database_filename: str = "", table_name: str = "", run_name: str = "") -> None:
    """Load table from database with the summary of the simulations

    Parameters
    ----------
    database_filename : `str`
        Name of the file with the database

    table_name : `str`
        Name of the table to be loaded
    """

    logger.debug(f" loading database table: {table_name} to locate run: {run_name}")

    # create dbase connection
    conn = sqlite3.connect(database_filename)

    # connect it with a cursor
    c = conn.cursor()

    data = c.execute(f"SELECT * FROM {table_name}")

    # row[0]: id
    # row[1]: run_name
    run_id = -1
    for row in data:
        if row[1] == run_name:
            run_id = row[0]
            break

    if run_id == -1:
        logger.error(f" could not find id for run: {run_name}. setting to -1")

    conn.close()

    return run_id
