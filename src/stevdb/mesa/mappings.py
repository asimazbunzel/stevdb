"""
Different useful mappings

Contains dictionaries with key-value mappings foir MESA simulations
"""

from pathlib import Path
from typing import Union

from ..io.logger import logger

customCodes = (
    'Darwin unstable',
    'mdot_atmospheric > max_mdot_rlof',
    'white-dwarf',
    'core-collapse',
)


def get_mesa_termination_codes(mesa_dir: Union[str, Path] = "") -> list:
    """Get termination codes from $MESA_DIR/star/private/star_private_def.f90"""

    codes = list()

    if isinstance(mesa_dir, str):
        mesa_dir = Path(mesa_dir)

    if not mesa_dir.is_dir():
        logger.error("`mesa_dir` not found. cannot get termination code from MESA")
        return codes

    fname = mesa_dir / "star/private/star_private_def.f90"
    if not fname.is_file():
        logger.error(f"`{fname}` not found. cannot get termination code from MESA")
        return codes

    with open(fname, "r") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith("termination_code_str(t"):
                termination_code = line.strip().split("=")[-1].strip().strip("'")
                codes.append(termination_code)

    return codes


def map_termination_code(mesa_dir: Union[str, Path] = "", termination_code: str = "") -> str:
    """Mapping between termination codes in MESA"""

    formatted_termination_code = ""

    mesa_default_codes = get_mesa_termination_codes(mesa_dir=mesa_dir)

    if termination_code in mesa_default_codes:
        formatted_termination_code = f"mesa default ({termination_code})"

    elif termination_code in customCodes:
        formatted_termination_code = f"mesa custom ({termination_code})"

    else:
        formatted_termination_code = f"unknown ({termination_code})"

    return formatted_termination_code
