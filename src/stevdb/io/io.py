"""Input/output module"""

from pathlib import Path
from typing import Union
import sys

import yaml


def load_yaml(fname: Union[str, Path]) -> dict:
    """Load configuration file with YAML format

    Parameters
    ----------
    fname : `str / Path`
        YAML filename

    Returns
    -------
    `yaml.load`
    """

    if isinstance(fname, Path):
        fname = str(fname)

    with open(fname, "r") as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def progress_bar(
    count: int,
    total: int,
    mark_count: int = 50,
    mark_char: str = "█",
    unmarked_char: str = ".",
    left_msg: str = "",
    right_msg: str = "",
) -> None:
    """Simple progress bar

    Obtained from:
    https://www.reddit.com/r/learnpython/comments/7hyyvr/python_progress_bar_used_in_conda/

    Parameters
    ----------
    count : `int`
       Iteration number

    total: `int`
       Total number of iterations to perform

    mark_count : `int`
       Length of bar

    mark_char : `misc`
       Character used for marking completion in bar

    unmarked_char : `misc`
       Same as above but for uncompleted part of bar

    left_msg : `string`
       Message of left of progress bar

    right_msg : `string`
       Message on right side of progress bar

    """

    # if msgs are longer than 15 characters, simply remove excess
    msg_left = left_msg if len(left_msg) <= 30 else left_msg[:30]
    msg_right = right_msg if len(right_msg) <= 30 else right_msg[:30]

    bar_filled = int(round(mark_count * count / float(total)))
    percent_str = str(round(100.0 * count / float(total), 1))
    marked_progress = mark_char * (bar_filled + 1)
    unmarked_progress = unmarked_char * (mark_count - bar_filled)
    progress = marked_progress + unmarked_progress

    sys.stdout.write(
        "\r{:<21} |{}| {:>6}% {:21}".format(
            msg_left, progress, percent_str, msg_right
        )
    )
    sys.stdout.flush()
