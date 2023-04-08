============
Installation
============

Cloning STEVDB
--------------

First, clone the repository in your computer:

.. code-block::

   git clone https://github.com/asimazbunzel/stevdb.git

or

.. code-block::

   git clone git@github.com:asimazbunzel/stevdb.git

depending if you have git set up or you are using an SSH key.

Installing STEVDB
-----------------

Once the repository is cloned in a local directory, `cd` into this new directory and run the
following code

.. code-block::

   pip install -U stevdb

This will create the executable `db-manager` that controls the creation of tables in a database
that must have been created with the `STEVMA <https://github.com/asimazbunzel/stevma>`__ code

Then, you can run

.. code-block::

   db-manager --help

or with `Poetry`

.. code-block::

   poetry run db-manager --help

.. note::

   USE A CONDA ENVIRONMENT

   The usage of a conda environment is strongly recommended as it will automatically
   handle the different versions of the libraries needed by the code to work

STEVDB development
------------------

  Here is how to set up STEVDB for development purposes. See also :ref:`Contributing` for how to
prepare your GitHub fork of the module.

Makefile usage
~~~~~~~~~~~~~~

`Makefile <https://github.com/asimazbunzel/stevdb/blob/develop/Makefile>`__ contains a lot of
functions for faster development.

1. Download and remove Poetry

To download and install Poetry run:

.. code-block::

  make poetry-download

To uninstall

.. code-block::

  make poetry-remove

2. Install all dependencies and pre-commit hooks

Install requirements:

.. code-block::

   make install

Pre-commit hooks coulb be installed after `git init` via

.. code-block::

  make pre-commit-install

3. Codestyle

Automatic formatting uses `pyupgrade`, `isort` and `black`.

.. code-block::

  make codestyle

  # or use synonym
  make formatting

Codestyle checks only, without rewriting files:

.. code-block::

  make check-codestyle

.. note::

   `check-codestyle` uses `isort`, `black` and `darglint` library

Update all dev libraries to the latest version using one comand

.. code-block::

  make update-dev-deps

4. Code security

.. code-block::

  make check-safety

This command launches `Poetry` integrity checks as well as identifies security issues with
`Safety` and `Bandit`.

.. code-block::

  make check-safety

5. Type checks

Run `mypy` static type checker

.. code-block::

  make mypy

And many more ! See much more information on this
`template <https://github.com/TezRomacH/python-package-template>`__
