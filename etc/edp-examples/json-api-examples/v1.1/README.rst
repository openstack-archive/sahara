=============================
 Sahara EDP JSON API Examples
=============================
------
 v1.1
------

Overview
========

This document provides a step-by-step guide to usage of the Sahara EDP API,
with JSON payload examples, covering:

* Data source creation in both swift and HDFS,
* Binary storage in both swift and the sahara database, and
* Job creation for Pig, Map/Reduce, Java, and Spark jobs.

Five example flows are provided:

* A Pig job, using swift for both data and binary storage.
* A Map/Reduce job, using HDFS data sources registered in sahara and swift
  for binary storage.
* A Java job, using raw HDFS data paths and the sahara database for binary
  storage.
* A Spark job without data inputs, using swift for binary storage.
* A shell job without data inputs, using the sahara database for binary
  storage.

Many other combinations of data source storage, binary storage, and job type
are possible. These examples are intended purely as a point of departure for
modification and experimentation for any sahara user who prefers a
command-line interface to UI (or who intends to automate sahara usage.)

Notes
=====

Formatting
----------

The json files provided make many assumptions, allowing the examples to be as
literal as possible. However, where objects created by the flow must refer to
one another's generated ids, Python dictionary-style is used.

Oozie is required for Hadoop
----------------------------

When the preconditions for a given example specify that you must have "an
active Hadoop cluster", that cluster must be running an Oozie process in all
cases, as sahara's EDP jobs are scheduled through Oozie in all Hadoop plugins.

Swift credentials
-----------------

For the sake of simplicity, these examples pass swift credentials to the API
when creating data sources, storing binaries, and executing jobs. Use of a
`swift proxy`_ can improve security by reducing the need to distribute and
store credentials.

.. _swift proxy: http://docs.openstack.org/developer/sahara/userdoc/advanced.configuration.guide.html

REST API usage
--------------

The CLI and Python sahara client provide their own authentication mechanisms
and endpoint discovery. If you wish to use the raw REST API, however, please
authenticate on all requests described below by passing an auth token provided
by Keystone for your tenant and user in header 'X-Auth-Token'.

For new sahara REST users, reference to the `Sahara EDP API Documentation`_
will be useful throughout these exercises.

.. _Sahara EDP API Documentation: http://developer.openstack.org/api-ref-data-processing-v1.1.html

Example 1: Pig, using swift
===========================

Preconditions
-------------

This example assumes the following:

1. Usage of an OpenStack user named "demo", with password "password".
2. An active Hadoop cluster exists in the demo user's project.
3. In the demo user's project, the following files are stored in swift in the
   container ``edp-examples``, as follows:

   * The file at ``edp-examples/edp-pig/trim-spaces/example.pig`` is stored
     at path ``pig-job/example.pig``.
   * The file at ``edp-examples/edp-pig/trim-spaces/udf.jar`` is stored at
     path ``pig-job/udf.jar``.
   * The file at ``edp-examples/edp-pig/trim-spaces/data/input`` is stored at
     path ``pig-job/data/input``.

Steps
-----

1. **Input**: POST the payload at ``data-sources/create.swift-pig-input.json``
   to your sahara endpoint's ``data-sources`` path. Note the new object's
   id.
2. **Output**: POST the payload at
   ``data-sources/create.swift-pig-output.json`` to your sahara endpoint's
   ``data-sources`` path. Note the new object's id.
3. **Script**: POST the payload at ``job-binaries/create.pig-job.json`` to
   your sahara endpoint's ``job-binaries`` path. Note the new object's id.
4. **UDF .jar**: POST the payload at ``job-binaries/create.pig-udf.json`` to
   your sahara endpoint's ``job-binaries`` path. Note the new object's id.
5. **Job**: Insert the script binary id from step 3 and the UDF binary id from
   step 4 into the payload at ``jobs/create.pig.json``. Then POST this file to
   your sahara endpoint's ``jobs`` path. Note the new object's id.
6. **Job Execution**: Insert your Hadoop cluster id, the input id from step 1,
   and the output id from step 2 into the payload at
   ``job-executions/execute.pig.json``. Then POST this file to your sahara
   endpoint at path ``jobs/{job id from step 5}/execute``.

Note
----

Pig jobs can take both arguments and parameters, though neither are needed
for the example job.


Example 2: Map/Reduce, using HDFS and swift
===========================================

Preconditions
-------------

This example assumes the following:

1. Usage of an OpenStack user named "demo", with password "password".
2. An active Hadoop cluster exists in the demo user's project, with the
   master node's HDFS available at URL
   ``hdfs://hadoop-cluster-master-001:8020/``.
3. In the demo user's project, the file at
   ``edp-examples/edp-mapreduce/edp-mapreduce.jar`` is stored in swift in the
   container ``edp-examples``, at path ``edp-mapreduce/edp-mapreduce.jar``.
4. A text file exists in your Hadoop cluster's HDFS at path
   ``/user/edp-examples/edp-map-reduce/input``.

Steps
-----

1. **Input**: POST the payload at
   ``data-sources/create.hdfs-map-reduce-input.json`` to your sahara
   endpoint's ``data-sources`` path. Note the new object's id.
2. **Output**: POST the payload at
   ``data-sources/create.hdfs-map-reduce-output.json`` to your sahara
   endpoint's ``data-sources`` path. Note the new object's id.
3. **Binary**: POST the payload at ``job-binaries/create.map-reduce.json`` to
   your sahara endpoint's ``job-binaries`` path. Note the new object's id.
4. **Job**: Insert the binary id from step 3 into the payload at
   ``jobs/create.map-reduce.json``. Then POST this file to your sahara
   endpoint's ``jobs`` path. Note the new object's id.
5. **Job Execution**: Insert your Hadoop cluster id, the input id from step 1,
   and the output id from step 2 into the payload at
   ``job-executions/execute.map-reduce.json``. Then POST this file to your
   sahara endpoint at path ``jobs/{job id from step 4}/execute``.


Example 3: Java, using raw HDFS and the sahara database
=======================================================

Preconditions
-------------

This example assumes the following:

1. Usage of an OpenStack user named "demo", with password "password".
2. An active Hadoop cluster exists in the demo user's project, with the
   master node's HDFS available at URL
   ``hdfs://hadoop-cluster-master-001:8020/``.
3. A text file exists in your Hadoop cluster's HDFS at path
   ``/user/edp-examples/edp-java/input``.

Steps
-----

1. **Internal Job Binary**: PUT the file at
   ``edp-examples/edp-java/edp-java.jar`` into your sahara endpoint at path
   ``job-binary-internals/edp-java.jar``. Note the new object's id.
2. **Job Binary**: Insert the internal job binary id from step 1 into the
   payload at ``job-binaries/create.java.json``. Then POST this file to your
   sahara endpoint's ``job-binaries`` path. Note the new object's id.
3. **Job**: Insert the binary id from step 2 into the payload at
   ``jobs/create.java.json``. Then POST this file to your sahara endpoint's
   ``jobs`` path. Note the new object's id.
4. **Job Execution**: Insert your Hadoop cluster id into the payload at
   ``job-executions/execute.java.json``. Then POST this file to your sahara
   endpoint at path ``jobs/{job id from step 3}/execute``.


Example 4: Spark, using swift
=============================

Preconditions
-------------

This example assumes the following:

1. Usage of an OpenStack user named "demo", with password "password".
2. An active Spark cluster exists in the demo user's project.
3. In the demo user's project, the file at
   ``edp-examples/edp-spark/spark-example.jar`` is stored in swift in the
   container ``edp-examples``, at path ``edp-spark/spark-example.jar``.

Steps
-----

1. **Job Binary**: POST the payload at ``job-binaries/create.spark.json``
   to your sahara endpoint's ``job-binaries`` path. Note the new object's id.
2. **Job**: Insert the binary id from step 1 into the payload at
   ``jobs/create.spark.json``. Then POST this file to your sahara endpoint's
   ``jobs`` path. Note the new object's id.
3. **Job Execution**: Insert your Spark cluster id into the payload at
   ``job-executions/execute.spark.json``. Then POST this file to your sahara
   endpoint at path ``jobs/{job id from step 2}/execute``.

Note
----

Spark jobs can use additional library binaries, but none are needed for the
example job.


Example 5: Shell script, using the sahara database
==================================================

Preconditions
-------------

This example assumes the following:

1. Usage of an OpenStack user named "demo", with password "password".
2. An active Hadoop cluster exists in the demo user's project.

Steps
-----

1. **Script File**: PUT the file at
   ``edp-examples/edp-shell/shell-example.sh`` into your sahara endpoint at
   path ``job-binary-internals/shell-example.sh``. Note the new object's id.
2. **Text File**: PUT the file at
   ``edp-examples/edp-shell/shell-example.txt`` into your sahara endpoint at
   path ``job-binary-internals/shell-example.txt``. Note the new object's id.
3. **Script Binary**: Insert the script file's id from step 1 into the payload
   at ``job-binaries/create.shell-script.json``. Then POST this file to your
   sahara endpoint's ``job-binaries`` path. Note the new object's id.
4. **Text Binary**: Insert the text file's id from step 2 into the payload
   at ``job-binaries/create.shell-text.json``. Then POST this file to your
   sahara endpoint's ``job-binaries`` path. Note the new object's id.
5. **Job**: Insert the binary ids from steps 3 and 4 into the payload at
   ``jobs/create.shell.json``. Then POST this file to your sahara endpoint's
   ``jobs`` path. Note the new object's id.
6. **Job Execution**: Insert your Hadoop cluster id into the payload at
   ``job-executions/execute.java.json``. Then POST this file to your sahara
   endpoint at path ``jobs/{job id from step 5}/execute``.
