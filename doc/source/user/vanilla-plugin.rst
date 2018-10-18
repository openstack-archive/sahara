Vanilla Plugin
==============

The vanilla plugin is a reference implementation which allows users to operate
a cluster with Apache Hadoop.

Since the Newton release Spark is integrated into the Vanilla plugin so you
can launch Spark jobs on a Vanilla cluster.

Images
------

For cluster provisioning, prepared images should be used.

.. list-table:: Support matrix for the `vanilla` plugin
   :widths: 15 15 20 15 35
   :header-rows: 1

   * - Version
       (image tag)
     - Distribution
     - Build method
     - Version
       (build parameter)
     - Notes

   * - 2.8.2
     - Ubuntu 16.04, CentOS 7
     - sahara-image-create
     - 2.8.2
     - Hive 2.3.2, Oozie 4.3.0

   * - 2.7.5
     - Ubuntu 16.04, CentOS 7
     - sahara-image-create
     - 2.7.5
     - Hive 2.3.2, Oozie 4.3.0

   * - 2.7.1
     - Ubuntu 16.04, CentOS 7
     - sahara-image-create
     - 2.7.1
     - Hive 0.11.0, Oozie 4.2.0

For more information about building image, refer to
:doc:`building-guest-images`.

Vanilla plugin requires an image to be tagged in Sahara Image Registry with
two tags: 'vanilla' and '<hadoop version>' (e.g. '2.7.1').

The image requires a username. For more information, refer to the
:doc:`registering-image` section.

Build settings
~~~~~~~~~~~~~~

When ``sahara-image-create`` is used, you can override few settings
by exporting the corresponding environment variables
before starting the build command:

* ``DIB_HADOOP_VERSION`` - version of Hadoop to install
* ``HIVE_VERSION`` - version of Hive to install
* ``OOZIE_DOWNLOAD_URL`` - download link for Oozie (we have built
  Oozie libs here: https://tarballs.openstack.org/sahara-extra/dist/oozie/)
* ``SPARK_DOWNLOAD_URL`` - download link for Spark

Vanilla Plugin Requirements
---------------------------

The image building tools described in :ref:`building-guest-images-label`
add the required software to the image and their usage is strongly suggested.
Nevertheless, here are listed the software that should be pre-loaded
on the guest image so that it can be used to create Vanilla clusters:

* ssh-client installed
* Java (version >= 7)
* Apache Hadoop installed
* 'hadoop' user created

See :doc:`hadoop-swift` for information on using Swift with your sahara cluster
(for EDP support Swift integration is currently required).

To support EDP, the following components must also be installed on the guest:

* Oozie version 4 or higher
* mysql/mariadb
* hive

Cluster Validation
------------------

When user creates or scales a Hadoop cluster using a Vanilla plugin,
the cluster topology requested by user is verified for consistency.

Currently there are the following limitations in cluster topology for Vanilla
plugin:

For Vanilla Hadoop version 2.x.x:

+ Cluster must contain exactly one namenode
+ Cluster can contain at most one resourcemanager
+ Cluster can contain at most one secondary namenode
+ Cluster can contain at most one historyserver
+ Cluster can contain at most one oozie and this process is also required
  for EDP
+ Cluster can't contain oozie without resourcemanager and without
  historyserver
+ Cluster can't have nodemanager nodes if it doesn't have resourcemanager
+ Cluster can have at most one hiveserver node.
+ Cluster can have at most one spark history server and this process is also
  required for Spark EDP (Spark is available since the Newton release).
