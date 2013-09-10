Integration tests for Savanna project
=====================================

How to run
----------

Create 3 config files for integration tests - `/savanna/tests/integration/configs/common_config.py`,
`/savanna/tests/integration/configs/hdp_config.py` and `/savanna/tests/integration/configs/vanilla_config.py`.
You can take a look at sample config files - `/savanna/tests/integration/configs/samples/common_config.py.sample`,
`/savanna/tests/integration/configs/samples/hdp_config.py.sample` and `/savanna/tests/integration/configs/samples/vanilla_config.py.sample`.
All values used in `/savanna/tests/integration/configs/parameters/common_parameters.py`,
`/savanna/tests/integration/configs/parameters/hdp_parameters.py` and `/savanna/tests/integration/configs/parameters/vanilla_parameters.py`
files are defaults, so, if they are applicable for your environment then you
can skip config file creation.

To run integration tests you should use the corresponding tox env: `tox -e integration`.

Contents
--------

This integration tests check work of "Vanilla" plugin and "HDP" plugin.

"Vanilla" plugin has as follows tests:
1. CRUD operation tests;
2. Hadoop test;
3. Swift test;
4. Cluster scaling test;
5. Test of Hadoop configuration files;
6. Image registry test.

"HDP" plugin has only Hadoop test.

<<<<<<<<<<<<<<<<<<<<<<<<<<<<< For "Vanilla" plugin >>>>>>>>>>>>>>>>>>>>>>>>>>>>

1. CRUD operation tests check CRUD operations for clusters, cluster templates
and node group templates.

2. Hadoop test checks Map Reduce "PI" job launch and Map Reduce "wordcount"
job launch. Also this test has a check for HDFS.

3. Swift test checks Swift availability for cluster.

4. Cluster scaling test checks cluster node addition and deletion.

5. Test of Hadoop configuration files checks presence of desired parameters in
Hadoop configuration files which were specified while cluster creation.

6. Image registry test checks image registry work (tags addition and deletion,
username and description property for image).

<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< For "HDP" plugin >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

Hadoop test checks Map Reduce "PI" job launch and Map Reduce "wordcount" job
launch. Also this test has a check for HDFS.
