Cloudera Plugin
===============

The Cloudera plugin is a Sahara plugin which allows the user to
deploy and operate a cluster with Cloudera Manager.

The Cloudera plugin is enabled in Sahara by default. You can manually
modify the Sahara configuration file (default /etc/sahara/sahara.conf) to
explicitly enable or disable it in "plugins" line.

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

   * - 5.13.0
     - Ubuntu 16.04, CentOS 7
     - sahara-image-pack
     - 5.13.0
     -

   * - 5.11.0
     - Ubuntu 16.04, CentOS 7
     - sahara-image-pack, sahara-image-create
     - 5.11.0
     -

   * - 5.9.0
     - Ubuntu 14.04, CentOS 7
     - sahara-image-pack, sahara-image-create
     - 5.9.0
     -

   * - 5.7.0
     - Ubuntu 14.04, CentOS 7
     - sahara-image-pack, sahara-image-create
     - 5.7.0
     -

For more information about building image, refer to
:doc:`building-guest-images`.

The cloudera plugin requires an image to be tagged in Sahara Image Registry
with two tags: 'cdh' and '<cloudera version>' (e.g. '5.13.0', '5.11.0',
'5.9.0', etc).

The default username specified for these images is different for each
distribution. For more information, refer to the
:doc:`registering-image` section.

Build settings
~~~~~~~~~~~~~~

It is possible to specify minor versions of CDH when ``sahara-image-create``
is used.
If you want to use a minor versions, export ``DIB_CDH_MINOR_VERSION``
before starting the build command, e.g.:

   .. sourcecode:: console

      export DIB_CDH_MINOR_VERSION=5.7.1

Services Supported
------------------

Currently below services are supported in both versions of Cloudera plugin:
HDFS, Oozie, YARN, Spark, Zookeeper, Hive, Hue, HBase. 5.3.0 version of
Cloudera Plugin also supported following services: Impala, Flume, Solr, Sqoop,
and Key-value Store Indexer. In version 5.4.0 KMS service support was added
based on version 5.3.0. Kafka 2.0.2 was added for CDH 5.5 and higher.

.. note::

    Sentry service is enabled in Cloudera plugin. However, as we do not enable
    Kerberos authentication in the cluster for CDH version < 5.5 (which is
    required for Sentry functionality) then using Sentry service will not
    really take any effect, and other services depending on Sentry will not do
    any authentication too.

High Availability Support
-------------------------

Currently HDFS NameNode High Availability is supported beginning with
Cloudera 5.4.0 version.  You can refer to :doc:`features` for the detail
info.

YARN ResourceManager High Availability is supported beginning with Cloudera
5.4.0 version. This feature adds redundancy in the form of an Active/Standby
ResourceManager pair to avoid the failure of single RM. Upon failover, the
Standby RM become Active so that the applications can resume from their last
check-pointed state.

Cluster Validation
------------------

When the user performs an operation on the cluster using a Cloudera plugin, the
cluster topology requested by the user is verified for consistency.

The following limitations are required in the cluster topology for all
cloudera plugin versions:

+ Cluster must contain exactly one manager.
+ Cluster must contain exactly one namenode.
+ Cluster must contain exactly one secondarynamenode.
+ Cluster must contain at least ``dfs_replication`` datanodes.
+ Cluster can contain at most one resourcemanager and this process is also
  required by nodemanager.
+ Cluster can contain at most one jobhistory and this process is also
  required for resourcemanager.
+ Cluster can contain at most one oozie and this process is also required
  for EDP.
+ Cluster can't contain oozie without datanode.
+ Cluster can't contain oozie without nodemanager.
+ Cluster can't contain oozie without jobhistory.
+ Cluster can't contain hive on the cluster without the following services:
  metastore, hive server, webcat and resourcemanager.
+ Cluster can contain at most one hue server.
+ Cluster can't contain hue server without hive service and oozie.
+ Cluster can contain at most one spark history server.
+ Cluster can't contain spark history server without resourcemanager.
+ Cluster can't contain hbase master service without at least one zookeeper
  and at least one hbase regionserver.
+ Cluster can't contain hbase regionserver without at least one hbase maser.

In case of 5.3.0, 5.4.0, 5.5.0, 5.7.x or 5.9.x version of Cloudera Plugin
there are few extra limitations in the cluster topology:

+ Cluster can't contain flume without at least one datanode.
+ Cluster can contain at most one sentry server service.
+ Cluster can't contain sentry server service without at least one zookeeper
  and at least one datanode.
+ Cluster can't contain solr server without at least one zookeeper and at
  least one datanode.
+ Cluster can contain at most one sqoop server.
+ Cluster can't contain sqoop server without at least one datanode,
  nodemanager and jobhistory.
+ Cluster can't contain hbase indexer without at least one datanode,
  zookeeper, solr server and hbase master.
+ Cluster can contain at most one impala catalog server.
+ Cluster can contain at most one impala statestore.
+ Cluster can't contain impala catalogserver without impala statestore,
  at least one impalad service, at least one datanode, and metastore.
+ If using Impala, the daemons must be installed on every datanode.

In case of version 5.5.0, 5.7.x or 5.9.x of Cloudera Plugin additional
services in the cluster topology are available:

+ Cluster can have the kafka service and several kafka brokers.

Enabling Kerberos security for cluster
--------------------------------------

If you want to protect your clusters using MIT Kerberos security you have to
complete a few steps below.

* If you would like to create a cluster protected by Kerberos security you
  just need to enable Kerberos by checkbox in the ``General Parameters``
  section of the cluster configuration. If you prefer to use the OpenStack CLI
  for cluster creation, you have to put the data below in the
  ``cluster_configs`` section:

  .. sourcecode:: console

     "cluster_configs": {
       "Enable Kerberos Security": true,
     }

  Sahara in this case will correctly prepare KDC server and will create
  principals along with keytabs to enable authentication for Hadoop services.

* Ensure that you have the latest hadoop-openstack jar file distributed
  on your cluster nodes. You can download one at
  ``https://tarballs.openstack.org/sahara-extra/dist/``

* Sahara will create principals along with keytabs for system users
  like ``hdfs`` and ``spark`` so that you will not have to
  perform additional auth operations to execute your jobs on top of the
  cluster.
