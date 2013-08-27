Integration tests for Savanna project
=====================================

How to run
----------

Create config file for integration tests: `/savanna/tests/integration/configs/itest.conf`.
You can take a look at sample config files - `/savanna/tests/integration/configs/itest.conf.sample`,
`/savanna/tests/integration/configs/itest.conf.sample-full`.
All values used in `/savanna/tests/integration/configs/config.py` file are
defaults, so, if they are applicable for your environment then you can skip
config file creation.

To run all integration tests you should use the corresponding tox env: `tox -e integration`.
In this case all tests will be launched except disabled tests.
Tests may be disabled in `/savanna/tests/integration/configs/config.py` file
or created config file `/savanna/tests/integration/configs/itest.conf`.

If you want to run integration tests for one plugin or a few plugins you should use
the corresponding tox env: `tox -e integration -- -a tags=<plugin_name>` or
`tox -e integration -- -a tags=<plugin_name_1>,<plugin_name_2>`.

For example: `tox -e integration -- -a tags=vanilla` or `tox -e integration -- -a tags=vanilla,hdp`

Contents
--------

TBD