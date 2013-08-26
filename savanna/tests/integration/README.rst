Integration tests for Savanna project
=====================================

How to run
----------

Create config file for integration tests - `/savanna/tests/integration/configs/config.py`.
You can take a look at the sample config file - `/savanna/tests/integration/configs/config.py.sample`.
All values used in `/savanna/tests/integration/configs/parameters.py` file are
defaults, so, if they are applicable for your environment then you can skip
config file creation.

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

"HDP" plugin has only Hadoop test. This Hadoop test checks Map Reduce "PI" job
launch and Map Reduce "wordcount" job launch. Also this test has a check
for HDFS.
