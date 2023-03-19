"""
Database module
"""

import sqlite3
import time
from collections import OrderedDict

import numpy as np

from .logging import logger


class Database:
    """Database driver"""

    def __init__(self):
        pass


def create_database(
    database_filename: str = "", table_name: str = "", table_dict: OrderedDict = OrderedDict()
) -> None:
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
    tstart: float = time.time()

    # maps between python and sqlite
    dtype_map = {
        None: "NULL",
        int: "INTEGER",
        float: "REAL",
        np.float64: "REAL",
        np.ndarray: "REAL",
        str: "TEXT",
        bytes: "BLOB",
        bool: "INTEGER",
    }

    cmd: str = f"CREATE TABLE IF NOT EXISTS {table_name} ("

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

    # commit creation command to SQLITE database
    commit_to_database(database_filename=database_filename, command=cmd)

    # (tend) timing of db creation
    tend: float = time.time()
    logger.debug(f" [database creation time: {tend-tstart:.2f} sec]")


def insert_run_into_database(
    database_filename: str = "", table_name: str = "", table_dict: OrderedDict = OrderedDict()
) -> None:
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
    tstart: float = time.time()

    cmd: str = f"INSERT INTO {table_name}"
    cmd_column_names: str = "("
    cmd_column_values: str = "("

    # append row depending on the type of the value
    for key, value in table_dict.items():
        if isinstance(value, str):
            cmd_column_names += f"{key}, "
            cmd_column_values += f"'{value}', "
        else:
            cmd_column_names += f"{key}, "
            cmd_column_values += f"{value}, "

    # write row to MESArun database
    cmd: str = f"{cmd} {cmd_column_names[:-2]}) VALUES {cmd_column_values[:-2]})"

    # commit insertion command to SQLITE database
    commit_to_database(database_filename=database_filename, command=cmd)

    # (tend) timing of db data insertion
    tend: float = time.time()
    logger.debug(f" [database record insertion time: {tend-tstart:.2f} sec]")


def commit_to_database(database_filename: str = "", command: str = "") -> None:
    """Commit a command to SQLite database

    Parameters
    ----------
    database_filename : `str`
        Name of the file with the database

    command : `str`
        Command to commit
    """

    # create database connection
    conn = sqlite3.connect(database_filename)

    # connect to it with a cursor
    c = conn.cursor()

    # append record to table
    c.execute(command)

    # commit changes
    conn.commit()

    # close connection
    conn.close()


def get_stevma_run_id(database_filename: str = "", table_name: str = "", run_name: str = "") -> int:
    """Retrieve id from table of runs created with the STEVMA code

    Parameters
    ----------
    database_filename : `str`
        Name of the file with the database

    table_name : `str`
        Name of the table created with STEVMA

    run_name : `str`
        Name of run to search for id

    Returns
    -------
    run_id : `int`
        Identifier of the run
    """

    logger.debug(f" getting id from STEVMA created table: `{table_name}`")

    # (tstart) for timing db data insertion
    tstart: float = time.time()

    # create database connection
    conn = sqlite3.connect(database_filename)

    # connect to it with a cursor
    c = conn.cursor()

    cmd: str = f"SELECT id FROM {table_name} WHERE run_name == '{run_name}';"

    # execute command
    c.execute(cmd)
    rows = c.fetchall()

    # (tend) timing of db data insertion
    tend: float = time.time()
    logger.debug(f" [elapsed time to retrieve id from database: {tend-tstart:.2f} sec]")

    return rows[0][0]


def has_final_data(run_id: int = -1, database_filename: str = "", table_name: str = "") -> bool:
    """Function that checks if run with id = `run_id` is already present in database `table_name`

    Parameters
    ----------
    run_id : `int`
        Identifier of the run

    database_filename : `str`
        Name of the file with the database

    table_name : `str`
        Name of the table created with STEVMA

    Returns
    -------
    has_data : `bool`
        Flag for the presence (absence) of final conditions of run in database
    """

    logger.debug(f" searching for data with id: `{run_id}` of table: `{table_name}`")

    # (tstart) for timing db data insertion
    tstart: float = time.time()

    has_data: bool = False

    # create database connection
    conn = sqlite3.connect(database_filename)

    # connect to it with a cursor
    c = conn.cursor()

    cmd: str = f"SELECT * FROM {table_name} WHERE id == '{run_id}';"

    # execute command
    try:
        c.execute(cmd)
        rows = c.fetchall()
    except sqlite3.OperationalError:
        return has_data

    print(rows)
    sys.exit(1)

    # (tend) timing of db data insertion
    tend: float = time.time()
    logger.debug(f" [elapsed time to retrieve id from database: {tend-tstart:.2f} sec]")

    return False
    # return rows[0][0]
