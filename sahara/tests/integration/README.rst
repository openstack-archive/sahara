Integration tests for Sahara project
====================================

How to run
----------

Create the config file for integration tests ``/sahara/tests/integration/configs/itest.conf``.
You can take a look at sample config file ``/sahara/tests/integration/configs/itest.conf.sample``
or ``/sahara/tests/integration/configs/itest.conf.sample-full``.
All values used in the ``/sahara/tests/integration/configs/config.py`` file are
defaults, so, if they are applicable for your environment then you can skip
config file creation.

To run all integration tests you should use the corresponding tox env:

.. sourcecode:: console

    $ tox -e integration
..

In this case all tests will be launched except disabled tests.
Tests can be disabled in the ``/sahara/tests/integration/configs/config.py``
file or in the ``/sahara/tests/integration/configs/itest.conf``.

If you want to run integration tests for one plugin, you should use the
corresponding tox env:

.. sourcecode:: console

    $ tox -e integration -- <tag>
..

<tag> may have the following values: ``transient``, ``vanilla1``, ``vanilla2``,
``hdp``.

For example, you want to run tests for the Vanilla plugin with the Hadoop
version 1.2.1. In this case you should use the following tox env:

.. sourcecode:: console

    $ tox -e integration -- vanilla1
..

If you want to run integration tests for a few plugins or their versions, you
should use the corresponding tox env:

.. sourcecode:: console

    $ tox -e integration -- <tag1> <tag2> ...
..

For example, you want to run tests for the Vanilla plugin with the Hadoop
version 2.4.1 and for the HDP plugin with the Hortonworks Data Platform version
1.3.2. In this case you should use the following tox env:

.. sourcecode:: console

    $ tox -e integration -- vanilla2 hdp
..

Here are a few more examples.

``tox -e integration -- transient`` will run test for transient cluster. In
this case cluster will be created via the Vanilla plugin with the Hadoop
version 1.2.1. More info about transient cluster see in section ``Contents``.

``tox -e integration -- hdp`` will run tests for the HDP plugin.

``tox -e integration -- transient vanilla2 hdp`` will run test for transient
cluster, tests for the Vanilla plugin with the Hadoop version 2.4.1 and tests
for the HDP plugin with the Hortonworks Data Platform version 1.3.2.

Contents
--------

The general checks performed by the integration tests are described below, and
for each plugin the applicable checks are listed.

1. Proper cluster creation. This test creates node group templates, a cluster
template and a cluster. All other test checks are executed on the created
cluster.

2. Cinder support. When the cluster is built, Cinder volumes are attached to
some cluster nodes (two 2 GB volumes per node). When cluster state is "Active",
SSH connection is established to nodes which have volumes. On each node
the bash command ``mount | grep <volume_mount_prefix> | wc -l`` is executed and
actual result is compared to the expected result.

3. Cluster configs. When the cluster is created, the bash script
``sahara/tests/integration/tests/resources/cluster_config_test_script.sh`` is
copied to all cluster nodes. On all nodes script checks that cluster configs
was properly applied.

4. Map Reduce. When the cluster is created, the bash script
``sahara/tests/integration/tests/resources/map_reduce_test_script.sh`` is
copied to all cluster nodes. On the master node this script runs Map Reduce
jobs "PI estimator" and "Word count". The input file for the job "Word count"
is generated with the bash command ``dmesg``. On other nodes this script
searches the Hadoop logs of completed jobs.

5. Swift availability. When the cluster is created, the bash script
``sahara/tests/integration/tests/resources/map_reduce_test_script.sh`` is
copied to the master node. The script generates a 1 mb file (we'll call it
"file1") with bash command ``dd if=/dev/urandom of=/tmp/test-file bs=1048576 count=1``.
The file is copied from local storage to HDFS storage, then it is uploaded from
HDFS storage to Swift (the command ``distcp``). Then the file is downloaded
back to HDFS storage from Swift. The file is copied from HDFS storage to local
storage (we'll call it "file2"). The script checks that md5 sums of file1 and
file2 are equal.

6. Elastic Data Processing (EDP). This test launches 4 types of EDP jobs on the
cluster. There are 4 types of EDP jobs: "Pig", "MapReduce",
"MapReduce.Streaming" and "Java".

7. Cluster scaling. This test adds 2 new node groups to the cluster (each node
group has 1 node), reduces count of nodes in 2 node groups from 1 node to 0
nodes (deletes 2 node groups) and increases count of nodes in 1 node group from
3 nodes to 4 nodes. All steps are executed in the same API request.

8. Transient cluster. In this test the cluster is created as a transient
cluster. No jobs are launched on the cluster. So the test checks that cluster
will be automatically deleted by Sahara after a while.

The Vanilla plugin with the Hadoop version 1.2.1 has the following checks:
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

1. Proper cluster creation.
2. Cinder support.
3. Cluster configs.
4. Map Reduce.
5. Elastic Data Processing (EDP).
6. Swift availability.
7. Cluster scaling.
8. Transient cluster.

The Vanilla plugin with the Hadoop version 2.4.1 has the following checks:
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

1. Proper cluster creation.
2. Cinder support.
3. Map Reduce.
4. Elastic Data Processing (EDP).
5. Swift availability.
6. Cluster scaling.

The HDP plugin has the following checks:
++++++++++++++++++++++++++++++++++++++++

1. Proper cluster creation.
2. Cinder support.
3. Map Reduce.
4. Elastic Data Processing (EDP).
5. Swift availability.
6. Cluster scaling.
