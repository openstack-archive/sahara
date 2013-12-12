Integration tests for Savanna project
=====================================

How to run
----------

Create the config file for integration tests: `/savanna/tests/integration/configs/itest.conf`.
You can take a look at sample config files - `/savanna/tests/integration/configs/itest.conf.sample`,
`/savanna/tests/integration/configs/itest.conf.sample-full`.
All values used in the `/savanna/tests/integration/configs/config.py` file are
defaults, so, if they are applicable for your environment then you can skip
config file creation.

To run all integration tests you should use the corresponding tox env: `tox -e integration`.
In this case all tests will be launched except disabled tests.
Tests may be disabled in the `/savanna/tests/integration/configs/config.py` file
or created the config file `/savanna/tests/integration/configs/itest.conf`.

If you want to run integration tests for one plugin or a few plugins you should use
the corresponding tox env: `tox -e integration -- <plugin_name>` or
`tox -e integration -- <plugin_name_1> <plugin_name_2>`.

For example: `tox -e integration -- vanilla` or `tox -e integration vanilla hdp`

Contents
--------

These integration tests check capacity for work of two plugins for Savanna:
Vanilla and HDP.

Vanilla plugin has the following checks:
++++++++++++++++++++++++++++++++++++++++

1. A cluster creation. This test create node group templates, a cluster
template and a cluster. All other test checks are performed on created cluster.

2. Test for a check of cluster configs. This test checks presence of desired
parameters in cluster configuration files which were specified during
the cluster creation. Desired configuration values are checked with GET-request
as well as directly in configuration files on the cluster.

3. Test for a check of Elastic Data Processing (EDP). This test launches
pig-job with jar-library and jar-job.

4. Test for a check of Hadoop (Map Reduce and HDFS). This test launches Map
Reduce jobs "PI estimator" and "Word count". Input file for job "Word count" is
generated with the bash command "dmesg".

5. Test for check of Swift availability. This test generates a 1 mb file.
The file is uploaded to HDFS storage, then to Swift storage with the command
"distcp". Further with the same command "distcp" the 1 mb file is downloaded
to HDFS storage from Swift. The 1 mb file is copied from HDFS to local storage
and md5 sums of both files is compared (the very first 1 mb file and the latest
file downloaded to local storage).

6. Test for a check of cluster scaling. This test add 2 new node groups,
resize 2 node groups to 0 nodes and resize 1 node group to 4 nodes.
All steps are performed in the same scaling request.

HDP plugin has the following checks:
++++++++++++++++++++++++++++++++++++

1. A cluster creation. This test create node group templates, a cluster
template and a cluster. All other test checks are performed on created cluster.

2. Test for a check of Hadoop (Map Reduce and HDFS). This test launches Map
Reduce jobs "PI estimator" and "Word count". Input file for job "Word count" is
generated with the bash command "dmesg".

3. Test for check of Swift availability. This test generates a 1 mb file.
The file is uploaded to HDFS storage, then to Swift storage with the command
"distcp". Further with the same command "distcp" the 1 mb file is downloaded
to HDFS storage from Swift. The 1 mb file is copied from HDFS to local storage
and md5 sums of both files is compared (the very first 1 mb file and the latest
file downloaded to local storage).

4. Test for a check of cluster scaling. This test add a 1 new node group and
resize 1 node group to 4 nodes. All steps are performed in the same scaling
request.
