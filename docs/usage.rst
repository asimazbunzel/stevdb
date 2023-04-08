=====
Usage
=====

After installing STEVDB, the command `db-manager` should be available. With it, everything is
controlled.

Some options are needed by this command to start managing the database of MESA-computed models.
These options can be seen by running `db-manager --help`:

- **-h, --help**            - show this help message and exit
- **-d, --debug**           - enable debug mode (default: False)
- **-C CONFIG_FNAME, --config-file CONFIG_FNAME**
                            - name of configuration file (default: None)
- **--show-log-name**       - display log filename and exit (default: False)
- **--show-config**         - display config info and exit (default: False)
- **--show-base-database**  - display database to standard output (default: False)

Configuration file
------------------

As mentioned before, the `-C` or `--config-file` option requires an input file with options to
manage the database and all the tables inside it.

Here is an example file (see `example` directory for this same information)

Note on debugging mode enable
-----------------------------

.. warning::

   A thorough explanation of debugging mode is not ready yet.

When running database manager on debug mode (`db-manager -d` or `db-manager --debug`), a log file
will be created (run `db-manager --show-log-name` to locate that file in your system). In it, the
*logging* module from the python standard library will output lots of information. This is the
best place to start digging in what the module is doing for each model in the grid already created
with the STEVMA code.

The manager has been coded such that a `DEBUG` string appearing in the log file is part of a core
method of the manager library: either doing a search of important parameters of a MESA model (e.g.,
looking for initial or final conditions) or creating/inserting/updating records into tables of the
database.

The best way to track from where this debugging flags are being called use a tool like `grep` to
search for a string. E.g., `grep "logger.debug(" stevdb/*.py` will look for every call to the
logging module in debug mode inside the root STEVDB module. This, of course, is a first guess and
should be continued to search for something more specific.
