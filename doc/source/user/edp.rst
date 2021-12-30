Elastic Data Processing (EDP)
=============================

Overview
--------

Sahara's Elastic Data Processing facility or :dfn:`EDP` allows the execution
of jobs on clusters created from sahara. EDP supports:

* Hive, Pig, MapReduce, MapReduce.Streaming, Java, and Shell job types on
  Hadoop clusters
* Spark jobs on Spark standalone clusters, MapR (v5.0.0 - v5.2.0) clusters,
  Vanilla clusters (v2.7.1) and CDH clusters (v5.3.0 or higher).
* storage of job binaries in the OpenStack Object Storage service (swift),
  the OpenStack Shared file systems service (manila), sahara's own database,
  or any S3-like object store
* access to input and output data sources in

  + HDFS for all job types
  + swift for all types excluding Hive
  + manila (NFS shares only) for all types excluding Pig
  + Any S3-like object store

* configuration of jobs at submission time
* execution of jobs on existing clusters or transient clusters

Interfaces
----------

The EDP features can be used from the sahara web UI which is described in the
:doc:`dashboard-user-guide`.

The EDP features also can be used directly by a client through the
`REST api <https://docs.openstack.org/api-ref/data-processing/>`_

EDP Concepts
------------

Sahara EDP uses a collection of simple objects to define and execute jobs.
These objects are stored in the sahara database when they are created,
allowing them to be reused. This modular approach with database persistence
allows code and data to be reused across multiple jobs.

The essential components of a job are:

* executable code to run
* input and output data paths, as needed for the job
* any additional configuration values needed for the job run

These components are supplied through the objects described below.

Job Binaries
++++++++++++

A :dfn:`Job Binary` object stores a URL to a single script or Jar file and
any credentials needed to retrieve the file.  The file itself may be stored
in the sahara internal database (**only API v1.1**), in swift,
or in manila.

Files in the sahara database are stored as raw bytes in a
:dfn:`Job Binary Internal` object. This object's sole purpose is to store a
file for later retrieval. No extra credentials need to be supplied for files
stored internally.

Sahara requires credentials (username and password) to access files stored in
swift unless swift proxy users are configured as described in
:doc:`../admin/advanced-configuration-guide`. The swift service must be
running in the same OpenStack installation referenced by sahara.

Sahara requires the following credentials/configs to access files stored in an
S3-like object store: ``accesskey``, ``secretkey``, ``endpoint``.
These credentials are specified through the `extra` in the body of the request
when creating a job binary referencing S3. The value of ``endpoint`` should
include a protocol: *http* or *https*.

To reference a binary file stored in manila, create the job binary with the
URL ``manila://{share_id}/{path}``. This assumes that you have already stored
that file in the appropriate path on the share. The share will be
automatically mounted to any cluster nodes which require access to the file,
if it is not mounted already.

There is a configurable limit on the size of a single job binary that may be
retrieved by sahara. This limit is 5MB and may be set with the
*job_binary_max_KB* setting in the :file:`sahara.conf` configuration file.

Jobs
++++

A :dfn:`Job` object specifies the type of the job and lists all of the
individual Job Binary objects that are required for execution. An individual
Job Binary may be referenced by multiple Jobs.  A Job object specifies a main
binary and/or supporting libraries depending on its type:

+-------------------------+-------------+-----------+
| Job type                | Main binary | Libraries |
+=========================+=============+===========+
| ``Hive``                | required    | optional  |
+-------------------------+-------------+-----------+
| ``Pig``                 | required    | optional  |
+-------------------------+-------------+-----------+
| ``MapReduce``           | not used    | required  |
+-------------------------+-------------+-----------+
| ``MapReduce.Streaming`` | not used    | optional  |
+-------------------------+-------------+-----------+
| ``Java``                | not used    | required  |
+-------------------------+-------------+-----------+
| ``Shell``               | required    | optional  |
+-------------------------+-------------+-----------+
| ``Spark``               | required    | optional  |
+-------------------------+-------------+-----------+
| ``Storm``               | required    | not used  |
+-------------------------+-------------+-----------+
| ``Storm Pyelus``        | required    | not used  |
+-------------------------+-------------+-----------+


Data Sources
++++++++++++

A :dfn:`Data Source` object stores a URL which designates the location of
input or output data and any credentials needed to access the location.

Sahara supports data sources in swift. The swift service must be running in
the same OpenStack installation referenced by sahara.

Sahara also supports data sources in HDFS. Any HDFS instance running on a
sahara cluster in the same OpenStack installation is accessible without
manual configuration. Other instances of HDFS may be used as well provided
that the URL is resolvable from the node executing the job.

Sahara supports data sources in manila as well. To reference a path on an NFS
share as a data source, create the data source with the URL
``manila://{share_id}/{path}``. As in the case of job binaries, the specified
share will be automatically mounted to your cluster's nodes as needed to
access the data source.

Finally, Sahara supports data sources referring to S3-like object stores. The
URL should be of the form ``s3://{bucket}/{path}``. Also, the following
credentials/configs are understood: ``accesskey``, ``secretkey``,
``endpoint``, ``bucket_in_path``, and ``ssl``. These credentials are specified
through the ``credentials`` attribute of the body of the request when creating
a data source referencing S3. The value of ``endpoint`` should **NOT** include
a protocol (*http* or *https*), unlike when referencing an S3 job binary. It
can also be noted that Sahara clusters can interact with S3-like stores even
when not using EDP, i.e. when manually operating the cluster instead. Consult
the `hadoop-aws documentation <https://hadoop.apache.org/docs/stable/hadoop-aws/tools/hadoop-aws/index.html>`_
for more information. Also, be advised that hadoop-aws will only write a job's
output into a bucket which already exists: it does not create new buckets.

Some job types require the use of data source objects to specify input and
output when a job is launched. For example, when running a Pig job the UI will
prompt the user for input and output data source objects.

Other job types like Java or Spark do not require the user to specify data
sources. For these job types, data paths are passed as arguments. For
convenience, sahara allows data source objects to be referenced by name or id.
The section `Using Data Source References as Arguments`_ gives further
details.


Job Execution
+++++++++++++

Job objects must be *launched* or *executed* in order for them to run on the
cluster. During job launch, a user specifies execution details including data
sources, configuration values, and program arguments. The relevant details
will vary by job type. The launch will create a :dfn:`Job Execution` object in
sahara which is used to monitor and manage the job.

To execute Hadoop jobs, sahara generates an Oozie workflow and submits it to
the Oozie server running on the cluster. Familiarity with Oozie is not
necessary for using sahara but it may be beneficial to the user. A link to
the Oozie web console can be found in the sahara web UI in the cluster
details.

For Spark jobs, sahara uses the *spark-submit* shell script and executes the
Spark job from the master node in case of Spark cluster and from the Spark
Job History server in other cases. Logs of spark jobs run by sahara can be
found on this node under the */tmp/spark-edp* directory.

.. _edp_workflow:

General Workflow
----------------

The general workflow for defining and executing a job in sahara is essentially
the same whether using the web UI or the REST API.

1. Launch a cluster from sahara if there is not one already available
2. Create all of the Job Binaries needed to run the job, stored in the sahara
   database, in swift, or in manila

   + When using the REST API and internal storage of job binaries, the Job
     Binary Internal objects must be created first
   + Once the Job Binary Internal objects are created, Job Binary objects may
     be created which refer to them by URL

3. Create a Job object which references the Job Binaries created in step 2
4. Create an input Data Source which points to the data you wish to process
5. Create an output Data Source which points to the location for output data
6. Create a Job Execution object specifying the cluster and Job object plus
   relevant data sources, configuration values, and program arguments

   + When using the web UI this is done with the
     :guilabel:`Launch On Existing Cluster` or
     :guilabel:`Launch on New Cluster` buttons on the Jobs tab
   + When using the REST API this is done via the */jobs/<job_id>/execute*
     method

The workflow is simpler when using existing objects. For example, to
construct a new job which uses existing binaries and input data a user may
only need to perform steps 3, 5, and 6 above. Of course, to repeat the same
job multiple times a user would need only step 6.

Specifying Configuration Values, Parameters, and Arguments
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Jobs can be configured at launch. The job type determines the kinds of values
that may be set:

+--------------------------+---------------+------------+-----------+
| Job type                 | Configuration | Parameters | Arguments |
|                          | Values        |            |           |
+==========================+===============+============+===========+
| ``Hive``                 | Yes           | Yes        | No        |
+--------------------------+---------------+------------+-----------+
| ``Pig``                  | Yes           | Yes        | Yes       |
+--------------------------+---------------+------------+-----------+
| ``MapReduce``            | Yes           | No         | No        |
+--------------------------+---------------+------------+-----------+
| ``MapReduce.Streaming``  | Yes           | No         | No        |
+--------------------------+---------------+------------+-----------+
| ``Java``                 | Yes           | No         | Yes       |
+--------------------------+---------------+------------+-----------+
| ``Shell``                | Yes           | Yes        | Yes       |
+--------------------------+---------------+------------+-----------+
| ``Spark``                | Yes           | No         | Yes       |
+--------------------------+---------------+------------+-----------+
| ``Storm``                | Yes           | No         | Yes       |
+--------------------------+---------------+------------+-----------+
| ``Storm Pyelus``         | Yes           | No         | Yes       |
+--------------------------+---------------+------------+-----------+

* :dfn:`Configuration values` are key/value pairs.

  + The EDP configuration values have names beginning with *edp.* and are
    consumed by sahara
  + Other configuration values may be read at runtime by Hadoop jobs
  + Currently additional configuration values are not available to Spark jobs
    at runtime

* :dfn:`Parameters` are key/value pairs. They supply values for the Hive and
  Pig parameter substitution mechanisms. In Shell jobs, they are passed as
  environment variables.
* :dfn:`Arguments` are strings passed as command line arguments to a shell or
  main program

These values can be set on the :guilabel:`Configure` tab during job launch
through the web UI or through the *job_configs* parameter when using the
*/jobs/<job_id>/execute* REST method.

In some cases sahara generates configuration values or parameters
automatically. Values set explicitly by the user during launch will override
those generated by sahara.

Using Data Source References as Arguments
+++++++++++++++++++++++++++++++++++++++++

Sometimes it's necessary or desirable to pass a data path as an argument to a
job. In these cases, a user may simply type out the path as an argument when
launching a job. If the path requires credentials, the user can manually add
the credentials as configuration values. However, if a data source object has
been created that contains the desired path and credentials there is no need
to specify this information manually.

As a convenience, sahara allows data source objects to be referenced by name
or id in arguments, configuration values, or parameters. When the job is
executed, sahara will replace the reference with the path stored in the data
source object and will add any necessary credentials to the job configuration.
Referencing an existing data source object is much faster than adding this
information by hand. This is particularly useful for job types like Java or
Spark that do not use data source objects directly.

There are two job configuration parameters that enable data source references.
They may be used with any job type and are set on the ``Configuration`` tab
when the job is launched:

* ``edp.substitute_data_source_for_name`` (default **False**) If set to
  **True**, causes sahara to look for data source object name references in
  configuration values, arguments, and parameters when a job is launched. Name
  references have the form **datasource://name_of_the_object**.

  For example, assume a user has a WordCount application that takes an input
  path as an argument. If there is a data source object named **my_input**, a
  user may simply set the **edp.substitute_data_source_for_name**
  configuration parameter to **True** and add **datasource://my_input** as an
  argument when launching the job.

* ``edp.substitute_data_source_for_uuid`` (default **False**) If set to
  **True**, causes sahara to look for data source object ids in configuration
  values, arguments, and parameters when a job is launched. A data source
  object id is a uuid, so they are unique. The id of a data source object is
  available through the UI or the sahara command line client. A user may
  simply use the id as a value.

Creating an Interface for Your Job
++++++++++++++++++++++++++++++++++

In order to better document your job for cluster operators (or for yourself
in the future), sahara allows the addition of an interface (or method
signature) to your job template. A sample interface for the Teragen Hadoop
example might be:

+---------+---------+-----------+-------------+----------+--------------------+
| Name    | Mapping | Location  | Value       | Required | Default            |
|         | Type    |           | Type        |          |                    |
+=========+=========+===========+=============+==========+====================+
| Example | args    |     0     | string      | false    | teragen            |
| Class   |         |           |             |          |                    |
+---------+---------+-----------+-------------+----------+--------------------+
| Rows    | args    |     1     | number      | true     | unset              |
+---------+---------+-----------+-------------+----------+--------------------+
| Output  | args    |     2     | data_source | false    | hdfs://ip:port/path|
| Path    |         |           |             |          |                    |
+---------+---------+-----------+-------------+----------+--------------------+
| Mapper  | configs | mapred.   | number      | false    | unset              |
| Count   |         | map.tasks |             |          |                    |
+---------+---------+-----------+-------------+----------+--------------------+

A "Description" field may also be added to each interface argument.

To create such an interface via the REST API, provide an "interface" argument,
the value of which consists of a list of JSON objects, as below:

.. code-block::

    [
        {
            "name": "Example Class",
            "description": "Indicates which example job class should be used.",
            "mapping_type": "args",
            "location": "0",
            "value_type": "string",
            "required": false,
            "default": "teragen"
        },
    ]

Creating this interface would allow you to specify a configuration for any
execution of the job template by passing an "interface" map similar to:

.. code-block::

    {
        "Rows": "1000000",
        "Mapper Count": "3",
        "Output Path": "hdfs://mycluster:8020/user/myuser/teragen-output"
    }

The specified arguments would be automatically placed into the args, configs,
and params for the job, according to the mapping type and location fields of
each interface argument. The final ``job_configs`` map would be:

.. code-block::

    {
        "job_configs": {
            "configs":
                {
                    "mapred.map.tasks": "3"
                },
            "args":
                [
                    "teragen",
                    "1000000",
                    "hdfs://mycluster:8020/user/myuser/teragen-output"
                ]
        }
    }

Rules for specifying an interface are as follows:

- Mapping Type must be one of ``configs``, ``params``, or ``args``. Only types
  supported for your job type are allowed (see above.)
- Location must be a string for ``configs`` and ``params``, and an integer for
  ``args``. The set of ``args`` locations must be an unbroken series of
  integers starting from 0.
- Value Type must be one of ``string``, ``number``, or ``data_source``. Data
  sources may be passed as UUIDs or as valid paths (see above.) All values
  should be sent as JSON strings. (Note that booleans and null values are
  serialized differently in different languages. Please specify them as a
  string representation of the appropriate constants for your data processing
  engine.)
- ``args`` that are not required must be given a default value.

The additional one-time complexity of specifying an interface on your template
allows a simpler repeated execution path, and also allows us to generate a
customized form for your job in the Horizon UI. This may be particularly
useful in cases in which an operator who is not a data processing job
developer will be running and administering the jobs.

Generation of Swift Properties for Data Sources
+++++++++++++++++++++++++++++++++++++++++++++++

If swift proxy users are not configured (see
:doc:`../admin/advanced-configuration-guide`) and a job is run with data
source objects containing swift paths, sahara will automatically generate
swift username and password configuration values based on the credentials
in the data sources. If the input and output data sources are both in swift,
it is expected that they specify the same credentials.

The swift credentials may be set explicitly with the following configuration
values:

      +------------------------------------+
      | Name                               |
      +====================================+
      | fs.swift.service.sahara.username   |
      +------------------------------------+
      | fs.swift.service.sahara.password   |
      +------------------------------------+

Setting the swift credentials explicitly is required when passing literal
swift paths as arguments instead of using data source references. When
possible, use data source references as described in
`Using Data Source References as Arguments`_.

Additional Details for Hive jobs
++++++++++++++++++++++++++++++++

Sahara will automatically generate values for the ``INPUT`` and ``OUTPUT``
parameters required by Hive based on the specified data sources.

Additional Details for Pig jobs
+++++++++++++++++++++++++++++++

Sahara will automatically generate values for the ``INPUT`` and ``OUTPUT``
parameters required by Pig based on the specified data sources.

For Pig jobs, ``arguments`` should be thought of as command line arguments
separated by spaces and passed to the ``pig`` shell.

``Parameters`` are a shorthand and are actually translated to the arguments
``-param name=value``

Additional Details for MapReduce jobs
+++++++++++++++++++++++++++++++++++++

**Important!**

If the job type is MapReduce, the mapper and reducer classes *must* be
specified as configuration values.

Note that the UI will not prompt the user for these required values; they must
be added manually with the ``Configure`` tab.

Make sure to add these values with the correct names:

+-----------------------------+----------------------------------------+
| Name                        | Example Value                          |
+=============================+========================================+
| mapred.mapper.new-api       | true                                   |
+-----------------------------+----------------------------------------+
| mapred.reducer.new-api      | true                                   |
+-----------------------------+----------------------------------------+
| mapreduce.job.map.class     | org.apache.oozie.example.SampleMapper  |
+-----------------------------+----------------------------------------+
| mapreduce.job.reduce.class  | org.apache.oozie.example.SampleReducer |
+-----------------------------+----------------------------------------+

Additional Details for MapReduce.Streaming jobs
+++++++++++++++++++++++++++++++++++++++++++++++

**Important!**

If the job type is MapReduce.Streaming, the streaming mapper and reducer
classes *must* be specified.

In this case, the UI *will* prompt the user to enter mapper and reducer
values on the form and will take care of adding them to the job configuration
with the appropriate names. If using the python client, however, be certain to
add these values to the job configuration manually with the correct names:

+-------------------------+---------------+
| Name                    | Example Value |
+=========================+===============+
| edp.streaming.mapper    | /bin/cat      |
+-------------------------+---------------+
| edp.streaming.reducer   | /usr/bin/wc   |
+-------------------------+---------------+

Additional Details for Java jobs
++++++++++++++++++++++++++++++++

Data Source objects are not used directly with Java job types. Instead, any
input or output paths must be specified as arguments at job launch either
explicitly or by reference as described in
`Using Data Source References as Arguments`_. Using data source references is
the recommended way to pass paths to Java jobs.

If configuration values are specified, they must be added to the job's
Hadoop configuration at runtime. There are two methods of doing this. The
simplest way is to use the **edp.java.adapt_for_oozie** option described
below. The other method is to use the code from
`this example <https://opendev.org/openstack/sahara-tests/src/branch/master/sahara_tests/scenario/defaults/edp-examples/edp-java/README.rst>`_
to explicitly load the values.

The following special configuration values are read by sahara and affect how
Java jobs are run:

* ``edp.java.main_class`` (required) Specifies the full name of the class
  containing ``main(String[] args)``

  A Java job will execute the **main** method of the specified main class. Any
  arguments set during job launch will be passed to the program through the
  **args** array.

* ``oozie.libpath`` (optional) Specifies configuration values for the Oozie
  share libs, these libs can be shared by different workflows

* ``edp.java.java_opts`` (optional) Specifies configuration values for the JVM

* ``edp.java.adapt_for_oozie`` (optional) Specifies that sahara should perform
  special handling of configuration values and exit conditions. The default is
  **False**.

  If this configuration value is set to **True**, sahara will modify
  the job's Hadoop configuration before invoking the specified **main** method.
  Any configuration values specified during job launch (excluding those
  beginning with **edp.**) will be automatically set in the job's Hadoop
  configuration and will be available through standard methods.

  Secondly, setting this option to **True** ensures that Oozie will handle
  program exit conditions correctly.

At this time, the following special configuration value only applies when
running jobs on a cluster generated by the Cloudera plugin with the
**Enable Hbase Common Lib** cluster config set to **True** (the default value):

* ``edp.hbase_common_lib`` (optional) Specifies that a common Hbase lib
  generated by sahara in HDFS be added to the **oozie.libpath**. This for use
  when an Hbase application is driven from a Java job. Default is **False**.

The **edp-wordcount** example bundled with sahara shows how to use
configuration values, arguments, and swift data paths in a Java job type. Note
that the example does not use the **edp.java.adapt_for_oozie** option but
includes the code to load the configuration values explicitly.

Additional Details for Shell jobs
+++++++++++++++++++++++++++++++++

A shell job will execute the script specified as ``main``, and will place any
files specified as ``libs`` in the same working directory (on both the
filesystem and in HDFS). Command line arguments may be passed to the script
through the ``args`` array, and any ``params`` values will be passed as
environment variables.

Data Source objects are not used directly with Shell job types but data source
references may be used as described in
`Using Data Source References as Arguments`_.

The **edp-shell** example bundled with sahara contains a script which will
output the executing user to a file specified by the first command line
argument.

Additional Details for Spark jobs
+++++++++++++++++++++++++++++++++

Data Source objects are not used directly with Spark job types. Instead, any
input or output paths must be specified as arguments at job launch either
explicitly or by reference as described in
`Using Data Source References as Arguments`_. Using data source references
is the recommended way to pass paths to Spark jobs.

Spark jobs use some special configuration values:

* ``edp.java.main_class`` (required) Specifies the full name of the class
  containing the Java or Scala main method:

  + ``main(String[] args)`` for Java
  + ``main(args: Array[String]`` for Scala

  A Spark job will execute the **main** method of the specified main class.
  Any arguments set during job launch will be passed to the program through the
  **args** array.

* ``edp.spark.adapt_for_swift`` (optional) If set to **True**, instructs
  sahara to modify the job's Hadoop configuration so that swift paths may be
  accessed. Without this configuration value, swift paths will not be
  accessible to Spark jobs. The default is **False**. Despite the name, the
  same principle applies to jobs which reference paths in S3-like stores.

* ``edp.spark.driver.classpath`` (optional) If set to empty string sahara
  will use default classpath for the cluster during job execution.
  Otherwise this will override default value for the cluster for particular
  job execution.

The **edp-spark** example bundled with sahara contains a Spark program for
estimating Pi.


Special Sahara URLs
-------------------

Sahara uses custom URLs to refer to objects stored in swift, in manila, in the
sahara internal database, or in S3-like storage. These URLs are usually not
meant to be used outside of sahara.

Sahara swift URLs passed to running jobs as input or output sources include a
".sahara" suffix on the container, for example:

``swift://container.sahara/object``

You may notice these swift URLs in job logs, however, you do not need to add
the suffix to the containers yourself. sahara will add the suffix if
necessary, so when using the UI or the python client you may write the above
URL simply as:

``swift://container/object``

Sahara internal database URLs have the form:

``internal-db://sahara-generated-uuid``

This indicates a file object in the sahara database which has the given uuid
as a key.

Manila NFS filesystem reference URLS take the form:

``manila://share-uuid/path``

This format should be used when referring to a job binary or a data source
stored in a manila NFS share.

For both job binaries and data sources, S3 urls take the form:

``s3://bucket/path/to/object``

Despite the above URL format, the current implementation of EDP will still
use the Hadoop ``s3a`` driver to access data sources. Botocore is used to
access job binaries.

EDP Requirements
================

The OpenStack installation and the cluster launched from sahara must meet the
following minimum requirements in order for EDP to function:

OpenStack Services
------------------

When a Hadoop job is executed, binaries are first uploaded to a cluster node
and then moved from the node local filesystem to HDFS. Therefore, there must
be an instance of HDFS available to the nodes in the sahara cluster.

If the swift service *is not* running in the OpenStack installation:

+ Job binaries may only be stored in the sahara internal database
+ Data sources require a long-running HDFS

If the swift service *is* running in the OpenStack installation:

+ Job binaries may be stored in swift or the sahara internal database
+ Data sources may be in swift or a long-running HDFS


Cluster Processes
-----------------

Requirements for EDP support depend on the EDP job type and plugin used for
the cluster. For example a Vanilla sahara cluster must run at least one
instance of these processes to support EDP:

* For Hadoop version 1:

  + jobtracker
  + namenode
  + oozie
  + tasktracker
  + datanode

* For Hadoop version 2:

  + namenode
  + datanode
  + resourcemanager
  + nodemanager
  + historyserver
  + oozie
  + spark history server


EDP Technical Considerations
============================

There are several things in EDP which require attention in order
to work properly. They are listed on this page.

Transient Clusters
------------------

EDP allows running jobs on transient clusters. In this case the cluster is
created specifically for the job and is shut down automatically once the job
is finished.

Two config parameters control the behaviour of periodic clusters:

* periodic_enable - if set to 'false', sahara will do nothing to a transient
   cluster once the job it was created for is completed. If it is set to
   'true', then the behaviour depends on the value of the next parameter.
* use_identity_api_v3 - set it to 'false' if your OpenStack installation
   does not provide keystone API v3. In that case sahara will not terminate
   unneeded clusters. Instead it will set their state to 'AwaitingTermination'
   meaning that they could be manually deleted by a user. If the parameter is
   set to 'true', sahara will itself terminate the cluster. The limitation is
   caused by lack of 'trusts' feature in Keystone API older than v3.

If both parameters are set to 'true', sahara works with transient clusters in
the following manner:

1. When a user requests for a job to be executed on a transient cluster,
   sahara creates such a cluster.
2. Sahara drops the user's credentials once the cluster is created but
   prior to that it creates a trust allowing it to operate with the
   cluster instances in the future without user credentials.
3. Once a cluster is not needed, sahara terminates its instances using the
   stored trust. sahara drops the trust after that.
