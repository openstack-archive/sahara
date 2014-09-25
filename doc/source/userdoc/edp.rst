Elastic Data Processing (EDP)
=============================

Overview
--------

Sahara's Elastic Data Processing facility or :dfn:`EDP` allows the execution of Hadoop jobs on clusters created from Sahara. EDP supports:

* Hive, Pig, MapReduce, and Java job types
* storage of job binaries in Swift or Sahara's own database
* access to input and output data sources in Swift or HDFS
* configuration of jobs at submission time
* execution of jobs on existing clusters or transient clusters

Interfaces
----------

The EDP features can be used from the Sahara web UI which is described in the :doc:`../horizon/dashboard.user.guide`.

The EDP features also can be used directly by a client through the :doc:`../restapi/rest_api_v1.1_EDP`.

EDP Concepts
------------

Sahara EDP uses a collection of simple objects to define and execute Hadoop jobs. These objects are stored in the Sahara database when they
are created, allowing them to be reused.  This modular approach with database persistence allows code and data to be reused across multiple jobs.

The essential components of a job are:

* executable code to run
* input data to process
* an output data location
* any additional configuration values needed for the job run

These components are supplied through the objects described below.

Job Binaries
++++++++++++

A :dfn:`Job Binary` object stores a URL to a single Pig script, Hive script, or Jar file and any credentials needed to retrieve the file.  The file itself may be stored in the Sahara internal database or in Swift.

Files in the Sahara database are stored as raw bytes in a :dfn:`Job Binary Internal` object.  This object's sole purpose is to store a file for later retrieval.  No extra credentials need to be supplied for files stored internally.

Sahara requires credentials (username and password) to access files stored in Swift. The Swift service must be running in the same OpenStack installation referenced by Sahara.

There is a configurable limit on the size of a single job binary that may be retrieved by Sahara.  This limit is 5MB and may be set with the *job_binary_max_KB* setting in the :file:`sahara.conf` configuration file.

Jobs
++++

A :dfn:`Job` object specifies the type of the job and lists all of the individual Job Binary objects that are required for execution. An individual Job Binary may be referenced by multiple Jobs.  A Job object specifies a main binary and/or supporting libraries depending on its type.

      +----------------+-------------+-----------+
      | Job type       | Main binary | Libraries |
      +================+=============+===========+
      | ``Hive``       | required    | optional  |
      +----------------+-------------+-----------+
      | ``Pig``        | required    | optional  |
      +----------------+-------------+-----------+
      | ``MapReduce``  | not used    | required  |
      +----------------+-------------+-----------+
      | ``Java``       | not used    | required  |
      +----------------+-------------+-----------+


Data Sources
++++++++++++

A :dfn:`Data Source` object stores a URL which designates the location of input or output data and any credentials needed to access the location.

Sahara supports data sources in Swift. The Swift service must be running in the same OpenStack installation referenced by Sahara.

Sahara also supports data sources in HDFS. Any HDFS instance running on a Sahara cluster in the same OpenStack installation is accessible without manual configuration. Other instances of HDFS may be used as well provided that the URL is resolvable from the node executing the job.

Job Execution
+++++++++++++

Job objects must be *launched* or *executed* in order for them to run on the cluster. During job launch, a user specifies execution details including data sources, configuration values, and program arguments. The relevant details will vary by job type. The launch will create a :dfn:`Job Execution` object in Sahara which is used to monitor and manage the job.

To execute the job, Sahara generates a workflow and submits it to the Oozie server running on the cluster. Familiarity with Oozie is not necessary for using Sahara but it may be beneficial to the user.  A link to the Oozie web console can be found in the Sahara web UI in the cluster details.

.. _edp_workflow:

General Workflow
----------------

The general workflow for defining and executing a job in Sahara is essentially the same whether using the web UI or the REST API.

1. Launch a cluster from Sahara if there is not one already available
2. Create all of the Job Binaries needed to run the job, stored in the Sahara database or in Swift

   + When using the REST API and internal storage of job binaries, there is an extra step here to first create the Job Binary Internal objects
   + Once the Job Binary Internal objects are created, Job Binary objects may be created which refer to them by URL

3. Create a Job object which references the Job Binaries created in step 2
4. Create an input Data Source which points to the data you wish to process
5. Create an output Data Source which points to the location for output data

(Steps 4 and 5 do not apply to Java job types. See `Additional Details for Java jobs`_)

6. Create a Job Execution object specifying the cluster and Job object plus relevant data sources, configuration values, and program arguments

   + When using the web UI this is done with the :guilabel:`Launch On Existing Cluster` or :guilabel:`Launch on New Cluster` buttons on the Jobs tab
   + When using the REST API this is done via the */jobs/<job_id>/execute* method

The workflow is simpler when using existing objects.  For example, to construct a new job which uses existing binaries and input data a user may only need to perform steps 3, 5, and 6 above.  Of course, to repeat the same job multiple times a user would need only step 6.

Specifying Configuration Values, Parameters, and Arguments
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Jobs can be configured at launch. The job type determines the kinds of values that may be set:

      +----------------+--------------+------------+-----------+
      | Job type       | Configration | Parameters | Arguments |
      |                | Values       |            |           |
      +================+==============+============+===========+
      | ``Hive``       | Yes          | Yes        | No        |
      +----------------+--------------+------------+-----------+
      | ``Pig``        | Yes          | Yes        | Yes       |
      +----------------+--------------+------------+-----------+
      | ``MapReduce``  | Yes          | No         | No        |
      +----------------+--------------+------------+-----------+
      | ``Java``       | Yes          | No         | Yes       |
      +----------------+--------------+------------+-----------+

* :dfn:`Configuration values` are key/value pairs. They set options for EDP, Oozie or Hadoop.

  + The EDP configuration values have names beginning with *edp.* and are consumed by Sahara
  + The Oozie and Hadoop configuration values may be read by running jobs

* :dfn:`Parameters` are key/value pairs. They supply values for the Hive and Pig parameter substitution mechanisms.
* :dfn:`Arguments` are strings passed to the pig shell or to a Java ``main()`` method.

These values can be set on the :guilabel:`Configure` tab during job launch through the web UI or through the *job_configs* parameter when using the  */jobs/<job_id>/execute* REST method.

In some cases Sahara generates configuration values or parameters automatically. Values set explicitly by the user during launch will override those generated by Sahara.

Generation of Swift Properties for Data Sources
+++++++++++++++++++++++++++++++++++++++++++++++

If a job is run with data sources in Swift, Sahara will automatically generate Swift username and password configuration values based on the credentials in the data sources.  If the input and output data sources are both in Swift, it is expected that they specify the same credentials.

The Swift credentials can be set explicitly with the following configuration values:

      +------------------------------------+
      | Name                               |
      +====================================+
      | fs.swift.service.sahara.username   |
      +------------------------------------+
      | fs.swift.service.sahara.password   |
      +------------------------------------+

Additional Details for Hive jobs
++++++++++++++++++++++++++++++++

Sahara will automatically generate values for the ``INPUT`` and ``OUTPUT`` parameters required by Hive based on the specified data sources.

Additional Details for Pig jobs
+++++++++++++++++++++++++++++++

Sahara will automatically generate values for the ``INPUT`` and ``OUTPUT`` parameters required by Pig based on the specified data sources.

For Pig jobs, ``arguments`` should be thought of as command line arguments separated by spaces and passed to the ``pig`` shell.

``Parameters`` are a shorthand and are actually translated to the arguments ``-param name=value``

Additional Details for MapReduce jobs
+++++++++++++++++++++++++++++++++++++

**Important!**

If the job type is MapReduce, the mapper and reducer classes *must* be specified as configuration values:

      +-------------------------+-----------------------------------------+
      | Name                    | Example Value                           |
      +=========================+=========================================+
      | mapred.mapper.class     | org.apache.oozie.example.SampleMapper   |
      +-------------------------+-----------------------------------------+
      | mapred.reducer.class    | org.apache.oozie.example.SampleReducer  |
      +-------------------------+-----------------------------------------+


Additional Details for Java jobs
++++++++++++++++++++++++++++++++

Java jobs use two configuration values that do not apply to other job types:

* ``edp.java.main_class`` (required) Specifies the class containing ``main(String[] args)``

* ``edp.java.java_opts`` (optional) Specifies configuration values for the JVM

A Java job will execute the ``main(String[] args)`` method of the specified main class.  There are two methods of passing
values to the ``main`` method:

* Passing values as arguments

  Arguments set during job launch will be passed in the ``String[] args`` array.

* Setting configuration values

  Any configuration values that are set can be read from a special file created by Oozie.

Data Source objects are not used with Java job types. Instead, any input or output paths must be passed to the ``main`` method
using one of the above two methods. Furthermore, if Swift data sources are used the configuration values listed in `Generation of Swift Properties for Data Sources`_  must be passed with one of the above two methods and set in the configuration by ``main``.

The ``edp-wordcount`` example bundled with Sahara shows how to use configuration values, arguments, and Swift data paths in a Java job type.


Special Sahara URLs
--------------------

Sahara uses custom URLs to refer to objects stored in Swift or the Sahara internal database.  These URLs are not meant to be used
outside of Sahara.

Sahara Swift URLs have the form:

  ``swift://container.sahara/object``

Sahara internal database URLs have the form:

  ``internal-db://sahara-generated-uuid``


EDP Requirements
================

The OpenStack installation and the cluster launched from Sahara must meet the following minimum requirements in order for EDP to function:

OpenStack Services
------------------

When a job is executed, binaries are first uploaded to a job tracker and then moved from the job tracker's local filesystem to HDFS. Therefore, there must be an instance of HDFS available to the nodes in the Sahara cluster.

If the Swift service *is not* running in the OpenStack installation

  + Job binaries may only be stored in the Sahara internal database
  + Data sources require a long-running HDFS

If the Swift service *is* running in the OpenStack installation

  + Job binaries may be stored in Swift or the Sahara internal database
  + Data sources may be in Swift or a long-running HDFS


Cluster Processes
-----------------

Requirements for EDP support depend on EDP job type and plugin used for the cluster.
For example Vanilla Sahara cluster must run at least one instance of these processes
to support EDP:

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


EDP Technical Considerations
============================

There are a several things in EDP which require attention in order
to work properly. They are listed on this page.

Transient Clusters
------------------

EDP allows running jobs on transient clusters. In this case the cluster is created
specifically for the job and is shut down automatically once the job is
finished.

Two config parameters control the behaviour of periodic clusters:

 * periodic_enable - if set to 'False', Sahara will do nothing to a transient
   cluster once the job it was created for is completed. If it is set to
   'True', then the behaviour depends on the value of the next parameter.
 * use_identity_api_v3 - set it to 'False' if your OpenStack installation
   does not provide Keystone API v3. In that case Sahara will not terminate
   unneeded clusters. Instead it will set their state to 'AwaitingTermination'
   meaning that they could be manually deleted by a user. If the parameter is
   set to 'True', Sahara will itself terminate the cluster. The limitation is
   caused by lack of 'trusts' feature in Keystone API older than v3.

If both parameters are set to 'True', Sahara works with transient clusters in
the following manner:

 1. When a user requests for a job to be executed on a transient cluster,
    Sahara creates such a cluster.
 2. Sahara drops the user's credentials once the cluster is created but
    prior to that it creates a trust allowing it to operate with the
    cluster instances in the future without user credentials.
 3. Once a cluster is not needed, Sahara terminates its instances using the
    stored trust. Sahara drops the trust after that.
