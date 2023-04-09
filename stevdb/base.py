"""Driver for the database of stellar models"""

from typing import Any

import argparse
import sys
from pathlib import Path

from stevdb.io import load_yaml, logger


class Manager:
    """Manager contains the configuration needed to create or update a database of stellar
    evolution models

    Options needed for the Manager are loaded from the command-line interface using an
    argument for the configuration file.
    """

    def __init__(self) -> None:

        # command line arguments
        self.args = self.parse_args()

        if self.args.config_fname is None:
            logger.critical(
                f"`configuration file option cannot be empty (maybe in the future we'll have defaults)`"
            )
            sys.exit(1)

        # always use pathlib
        if isinstance(self.args.config_fname, str):
            if len(self.args.config_fname) == 0:
                logger.critical("empty configuration file not available right now")
                sys.exit(1)

            self.args.config_fname = Path(self.args.config_fname)

        # load configuration
        self.config = self.load_config_file()

    def init_args(self) -> argparse.ArgumentParser:
        """Initialize parser of command line arguments

        Returns
        -------
        `argparse.ArgumentParser`
        """

        parser = argparse.ArgumentParser(
            prog="db-manager",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="create and/or update a database of stellar evolution simulations",
        )

        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            default=False,
            dest="debug",
            help="enable debug mode",
        )

        parser.add_argument(
            "-C",
            "--config-file",
            dest="config_fname",
            help="name of configuration file",
        )

        parser.add_argument(
            "--show-log-name",
            action="store_true",
            default=False,
            dest="log_fname",
            help="display log filename and exit",
        )

        parser.add_argument(
            "--show-config",
            action="store_true",
            default=False,
            dest="show_config",
            help="display config info and exit",
        )

        parser.add_argument(
            "--show-base-database",
            action="store_true",
            default=False,
            dest="show_db",
            help="display database to standard output",
        )

        return parser

    def parse_args(self) -> argparse.Namespace:
        """Parse command line arguments

        Returns
        -------
        `argparse.Namespace`
        """

        # parse initial arguments via cli
        parser = self.init_args()

        # print help msg if no arguments were given
        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)

        # get parsed arguments
        args = parser.parse_args()

        # if debug is True
        if args.debug:
            from logging import DEBUG

            logger.setLevel(DEBUG)

        # print cli arguments to log file
        msg = "command line arguments are: "
        for k, v in sorted(vars(args).items()):
            msg += f"{k}: {v} "
        logger.debug(msg[:-1])

        return args

    def load_config_file(self) -> Any:
        """Load configuration file with options for the manager

        Returns
        -------
        config : `dict`
            Dictionary with the configuration options of the Manager
        """

        logger.info("load configuration options from file")

        if not self.args.config_fname.exists():
            logger.critical(
                f"error while trying to load configuration file. No such file found: `{self.args.config_fname}`"
            )
            sys.exit(1)

        return load_yaml(self.args.config_fname)
