============
Installation
============


Cloning STEVDB
--------------

Clone the repository in your computer:

.. code-block::

   git clone https://github.com/asimazbunzel/stevdb.git

or

.. code-block::

   git clone git@github.com:asimazbunzel/stevdb.git

depending whether git is installed in your computer and if you are using an SSH key or not.

Installing STEVDB
-----------------

Once the repository is in your computer, `cd` into the new directory and run the following
code

.. code-block::

   pip install .

This will create an executable called `db-manager` that will handle the creation of the
database of MESA runs.

.. note::

   USE A CONDA ENVIRONMENT

   The usage of a conda environment is strongly recommended as it will automatically handle
   the different version of the libraries needed by the code to work
