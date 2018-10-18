Spark Plugin
============

The Spark plugin for sahara provides a way to provision Apache Spark clusters
on OpenStack in a single click and in an easily repeatable fashion.

Currently Spark is installed in standalone mode, with no YARN or Mesos
support.

Images
------

For cluster provisioning, prepared images should be used.

.. list-table:: Support matrix for the `spark` plugin
   :widths: 15 15 20 15 35
   :header-rows: 1

   * - Version
       (image tag)
     - Distribution
     - Build method
     - Version
       (build parameter)
     - Notes

   * - 2.3
     - Ubuntu 16.04
     - sahara-image-create
     - 2.3.0
     - based on CDH 5.11

   * - 2.2
     - Ubuntu 16.04
     - sahara-image-create
     - 2.2.0
     - based on CDH 5.11

For more information about building image, refer to
:doc:`building-guest-images`.

The Spark plugin requires an image to be tagged in the sahara image registry
with two tags: 'spark' and '<Spark version>' (e.g. '1.6.0').

The image requires a username. For more information, refer to the
:doc:`registering-image` section.

Note that the Spark cluster is deployed using the scripts available in the
Spark distribution, which allow the user to start all services (master and
slaves), stop all services and so on. As such (and as opposed to CDH HDFS
daemons), Spark is not deployed as a standard Ubuntu service and if the
virtual machines are rebooted, Spark will not be restarted.

Build settings
~~~~~~~~~~~~~~

When ``sahara-image-create`` is used, you can override few settings
by exporting the corresponding environment variables
before starting the build command:

* ``SPARK_DOWNLOAD_URL`` - download link for Spark

Spark configuration
-------------------

Spark needs few parameters to work and has sensible defaults. If needed they
can be changed when creating the sahara cluster template. No node group
options are available.

Once the cluster is ready, connect with ssh to the master using the `ubuntu`
user and the appropriate ssh key. Spark is installed in `/opt/spark` and
should be completely configured and ready to start executing jobs. At the
bottom of the cluster information page from the OpenStack dashboard, a link to
the Spark web interface is provided.

Cluster Validation
------------------

When a user creates an Hadoop cluster using the Spark plugin, the cluster
topology requested by user is verified for consistency.

Currently there are the following limitations in cluster topology for the
Spark plugin:

+ Cluster must contain exactly one HDFS namenode
+ Cluster must contain exactly one Spark master
+ Cluster must contain at least one Spark slave
+ Cluster must contain at least one HDFS datanode

The tested configuration co-locates the NameNode with the master and a
DataNode with each slave to maximize data locality.
