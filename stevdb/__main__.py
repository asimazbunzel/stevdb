# type: ignore[attr-defined]
import os
import platform

from stevdb import version


def main():
    """Main driver for stellar evolution manager"""

    print("********************************************************")
    print("          Stellar Evolution Database Manager            ")
    print("********************************************************")
    print("initialize database manager for stellar evolution models")

    curr_dir = os.getcwd()

    print(f"current working directory is `{curr_dir}`")
    print(f"{platform.python_implementation()} {platform.python_version()} detected")


if __name__ == "__main__":
    main()
