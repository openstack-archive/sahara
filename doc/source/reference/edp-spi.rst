Elastic Data Processing (EDP) SPI
=================================

The EDP job engine objects provide methods for creating, monitoring, and
terminating jobs on Sahara clusters. Provisioning plugins that support EDP
must return an EDP job engine object from the :ref:`get_edp_engine` method
described in :doc:`plugin-spi`.

Sahara provides subclasses of the base job engine interface that support EDP
on clusters running Oozie, Spark, and/or Storm. These are described below.

.. _edp_spi_job_types:

Job Types
---------

Some of the methods below test job type. Sahara supports the following string
values for job types:

* Hive
* Java
* Pig
* MapReduce
* MapReduce.Streaming
* Spark
* Shell
* Storm

.. note::
    Constants for job types are defined in *sahara.utils.edp*.

Job Status Values
-----------------

Several of the methods below return a job status value. A job status value is
a dictionary of the form:

{'status': *job_status_value*}

where *job_status_value* is one of the following string values:

* DONEWITHERROR
* FAILED
* TOBEKILLED
* KILLED
* PENDING
* RUNNING
* SUCCEEDED

Note, constants for job status are defined in *sahara.utils.edp*

EDP Job Engine Interface
------------------------

The sahara.service.edp.base_engine.JobEngine class is an
abstract class with the following interface:


cancel_job(job_execution)
~~~~~~~~~~~~~~~~~~~~~~~~~

Stops the running job whose id is stored in the job_execution object.

*Returns*: None if the operation was unsuccessful or an updated job status
value.

get_job_status(job_execution)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the current status of the job whose id is stored in the job_execution
object.

*Returns*: a job status value.


run_job(job_execution)
~~~~~~~~~~~~~~~~~~~~~~

Starts the job described by the job_execution object

*Returns*: a tuple of the form (job_id, job_status_value, job_extra_info).

* *job_id* is required and must be a string that allows the EDP engine to
  uniquely identify the job.
* *job_status_value* may be None or a job status value
* *job_extra_info* may be None or optionally a dictionary that the EDP engine
  uses to store extra information on the job_execution_object.


validate_job_execution(cluster, job, data)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Checks whether or not the job can run on the cluster with the specified data.
Data contains values passed to the */jobs/<job_id>/execute* REST API method
during job launch. If the job cannot run for any reason, including job
configuration, cluster configuration, or invalid data, this method should
raise an exception.

*Returns*: None

get_possible_job_config(job_type)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns hints used by the Sahara UI to prompt users for values when
configuring and launching a job. Note that no hints are required.

See :doc:`../user/edp` for more information on how configuration values,
parameters, and arguments are used by different job types.

*Returns*: a dictionary of the following form, containing hints for configs,
parameters, and arguments for the job type:

{'job_config': {'configs': [], 'params': {}, 'args': []}}

* *args* is a list of strings
* *params* contains simple key/value pairs
* each item in *configs* is a dictionary with entries
  for 'name' (required), 'value', and 'description'


get_supported_job_types()
~~~~~~~~~~~~~~~~~~~~~~~~~

This method returns the job types that the engine supports. Not all engines
will support all job types.

*Returns*: a list of job types supported by the engine.

Oozie Job Engine Interface
--------------------------

The sahara.service.edp.oozie.engine.OozieJobEngine class is derived from
JobEngine. It provides implementations for all of the methods in the base
interface but adds a few more abstract methods.

Note that the *validate_job_execution(cluster, job, data)* method does basic
checks on the job configuration but probably should be overloaded to include
additional checks on the cluster configuration. For example, the job engines
for plugins that support Oozie add checks to make sure that the Oozie service
is up and running.


get_hdfs_user()
~~~~~~~~~~~~~~~

Oozie uses HDFS to distribute job files. This method gives the name of the
account that is used on the data nodes to access HDFS (such as 'hadoop' or
'hdfs'). The Oozie job engine expects that HDFS contains a directory for this
user under */user/*.

*Returns*: a string giving the username for the account used to access HDFS on
the cluster.


create_hdfs_dir(remote, dir_name)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The remote object *remote* references a node in the cluster.  This method
creates the HDFS directory *dir_name* under the user specified by
*get_hdfs_user()* in the HDFS accessible from the specified node. For example,
if the HDFS user is 'hadoop' and the dir_name is 'test' this method would
create '/user/hadoop/test'.

The reason that this method is broken out in the interface as an abstract
method is that different versions of Hadoop treat path creation differently.

*Returns*: None


get_oozie_server_uri(cluster)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the full URI for the Oozie server, for example
*http://my_oozie_host:11000/oozie*.  This URI is used by an Oozie client to
send commands and queries to the Oozie server.

*Returns*: a string giving the Oozie server URI.


get_oozie_server(self, cluster)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the node instance for the host in the cluster running the Oozie
server.

*Returns*: a node instance.


get_name_node_uri(self, cluster)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the full URI for the Hadoop NameNode, for example
*http://master_node:8020*.

*Returns*: a string giving the NameNode URI.

get_resource_manager_uri(self, cluster)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns the full URI for the Hadoop JobTracker for Hadoop version 1 or the
Hadoop ResourceManager for Hadoop version 2.

*Returns*: a string giving the JobTracker or ResourceManager URI.

Spark Job Engine
----------------

The sahara.service.edp.spark.engine.SparkJobEngine class provides a full EDP
implementation for Spark standalone clusters.

.. note::
    The *validate_job_execution(cluster, job, data)* method does basic
    checks on the job configuration but probably should be overloaded to
    include additional checks on the cluster configuration. For example, the
    job engine returned by the Spark plugin checks that the Spark version is
    >= 1.0.0 to ensure that *spark-submit* is available.

get_driver_classpath(self)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns driver class path.

*Returns*: a string of the following format ' --driver-class-path
*class_path_value*'.
