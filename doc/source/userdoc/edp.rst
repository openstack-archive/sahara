Elastic Data Processing (EDP)
=============================

Overview
--------

Savanna's Elastic Data Processing facility or :dfn:`EDP` allows the execution of MapReduce jobs on clusters created from Savanna. EDP supports:

* execution of Hive scripts, Pig scripts and Jar files (:dfn:`job binaries`)
* storage of job binaries in Swift or Savanna's own database
* access to input and output data sources in Swift
* configuration of jobs at submission time
* execution of jobs on existing clusters or transient clusters

Interfaces
----------

The EDP features can be used from the Savanna web UI which is described in the :doc:`../horizon/dashboard.user.guide`.

The EDP features also can be used directly by a client through the :doc:`rest_api_v1.1_EDP`.

EDP Concepts
------------

Savanna EDP uses a collection of simple objects to define and execute MapReduce jobs.  These objects are stored in the Savanna database when they
are created, allowing them to be reused.  This modular approach with database persistence allows code and data to be reused across multiple jobs.

The essential components of a job are:

* executable code to run
* input data to process
* an output data location
* any additional configuration parameters needed for the job run

These components are supplied through the objects described below.

Job Binaries
++++++++++++

A :dfn:`Job Binary` object stores a URL to a single Pig script, Hive script, or Jar file and any credentials needed to retrieve the file.  The file may be stored in the Savanna internal database or in Swift.

Job binaries in the Savanna database are stored as raw bytes in a :dfn:`Job Binary Internal` object.  If you review the REST API or the code you will see references to it.  This object's sole purpose is to store a file for later retrieval.  No extra credentials need to be supplied for files stored internally.

Job binaries may be stored in Swift as well.  Currently, the Swift service must be running as part of the same OpenStack installation where Savanna is running.  Credentials (username and password) must be supplied that allow Savanna to authenticate to Swift and retrieve the file.

There is currently a configurable limit on the size of a single job binary that may be retrieved by Savanna.  This limit is 5MB and may be set with the *job_binary_max_KB* setting in the :file:`savanna.conf` configuration file.

Note, the URLs used by Savanna have special prefixes and are not intended to be used to reference job binaries outside of Savanna.

Jobs
++++

A :dfn:`Job` object specifies the type of the job and lists all of the individual Job Binary objects that are required for execution.  This supports code reuse since an individual Job Binary may be referenced by multiple Jobs.  A Job object may specify a main binary and supporting libraries.

Currently for Jar job types, the main binary is *not* applicable.  All binaries should be specified as supporting libraries, and the mapper and reducer classes *must* be specified with configuration parameters.  See the :ref:`edp_workflow` section for notes on setting mapper and reducer configs.

If the job type is Hive or Pig, a main binary *must* be specified even when supporting libraries are specified.


Data Sources
++++++++++++

A :dfn:`Data Source` object stores a URL which designates the location of input or output data and any credentials needed to access the location.  Currently Savanna supports input and output data in Swift. Currently, the Swift service must be running as part of the same OpenStack installation where Savanna is running.

Job Execution
+++++++++++++

A :dfn:`Job Execution` object pulls other objects together to execute the job.  It specifies a Job object, input Data Source, output Data Source, any necessary configuration parameters, and the cluster on which to run.  The Job Execution object also reports status about the job as it runs.

.. _edp_workflow:

Workflow
--------

The general workflow for defining and executing a MapReduce job in Savanna is essentially the same whether using the web UI or the REST API.

1. Launch a cluster from Savanna if there is not one already available
2. Create all of the Job Binaries needed to run the job, stored in the Savanna database or in Swift

   + When using the REST API and internal storage of job binaries, there is an extra step here to first create the Job Binary Internal objects
   + Once the Job Binary Internal objects are created, Job Binary objects may be created which refer to them via a savanna-db:// URL

3. Create a Job object which references the Job Binaries created in step 2
4. Create an input Data Source which points to the data you wish to process
5. Create an output Data Source which points to the location for output data
6. Create a Job Execution object specifying the Job object, input Data Source, output Data Source, and configuration parameters

   + When using the web UI this is done with the :guilabel:`Launch On Existing Cluster` or :guilabel:`Launch on New Cluster` buttons on the Jobs tab
   + When using the REST API this is done via the */jobs/<job_id>/execute* method
   + In both cases Savanna constructs and launches a Job Execution object as a single step on behalf of the user based on the supplied values

   **Important!**

   If the job type is Jar, the mapper and reducer classes *must* be specified as configuration parameters.  This can be done on the :guilabel:`Configure` tab during job launch through the web UI or through the *job_configs* parameter when using the  */jobs/<job_id>/execute* REST method.

      +-------------------------+-----------------------------------------+
      | Parameter               | Example Value                           |
      +=========================+=========================================+
      | mapred.mapper.class     | org.apache.oozie.example.SampleMapper   |
      +-------------------------+-----------------------------------------+
      | mapred.reducer.class    | org.apache.oozie.example.SampleReducer  |
      +-------------------------+-----------------------------------------+

The workflow is simpler when using existing objects.  For example, to construct a new job which uses existing binaries and input data a user may only need to perform steps 3, 5, and 6 above.  Of course, to repeat the same job multiple times a user would need only step 6.


EDP Technical Considerations
============================

There are a several things in EDP which require attention in order
to work properly. They are listed on this page.

Transient Clusters
------------------

EDP allows running jobs on transient clusters. That way the cluster is created
specifically for the job and is shut down automatically once the job is
finished.

Two config parameters control the behaviour of periodic clusters:

 * periodic_enable - if set to 'False', Savanna will do nothing to a transient
   cluster once the job it was created for is completed. If it is set to
   'True', then the behaviour depends on the value of the next parameter.
 * use_identity_api_v3 - set it to 'False' if your OpenStack installation
   does not provide Keystone API v3. In that case Savanna will not terminate
   unneeded clusters. Instead it will set their state to 'AwaitingTermination'
   meaning that they could be manually deleted by a user. If the parameter is
   set to 'True', Savanna will itself terminate the cluster. The limitation is
   caused by lack of 'trusts' feature in Keystone API older than v3.

If both parameters are set to 'True', Savanna works with transient clusters in
the following manner:

 1. When a user requests for a job to be executed on a transient cluster,
    Savanna creates such a cluster.
 2. Savanna drops the user's credentials once the cluster is created but
    prior to that it creates a trust allowing it to operate with the
    cluster instances in the future without user credentials.
 3. Once a cluster is not needed, Savanna terminates its instances using the
    stored trust. Savanna drops the trust after that.
