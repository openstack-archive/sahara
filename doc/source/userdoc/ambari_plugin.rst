
Ambari Plugin
=============
The Ambari sahara plugin provides a way to provision
clusters with Hortonworks Data Platform on OpenStack using templates in a
single click and in an easily repeatable fashion. The sahara controller serves
as the glue between Hadoop and OpenStack. The Ambari plugin mediates between
the sahara controller and Apache Ambari in order to deploy and configure Hadoop
on OpenStack. Core to the HDP Plugin is Apache Ambari
which is used as the orchestrator for deploying HDP on OpenStack. The Ambari
plugin uses Ambari Blueprints for cluster provisioning.

Apache Ambari Blueprints
------------------------
Apache Ambari Blueprints is a portable document definition, which provides a
complete definition for an Apache Hadoop cluster, including cluster topology,
components, services and their configurations. Ambari Blueprints can be
consumed by the Ambari plugin to instantiate a Hadoop cluster on OpenStack. The
benefits of this approach is that it allows for Hadoop clusters to be
configured and deployed using an Ambari native format that can be used with as
well as outside of OpenStack allowing for clusters to be re-instantiated in a
variety of environments.

Images
------
The sahara Ambari plugin is using minimal (operating system only) images.

For more information about Ambari images, refer to
https://github.com/openstack/sahara-image-elements.

You could download well tested and up-to-date prepared images from
http://sahara-files.mirantis.com/images/upstream/

HDP plugin requires an image to be tagged in sahara Image Registry with two
tags: 'ambari' and '<plugin version>' (e.g. '2.3').

Also in the Image Registry you will need to specify username for an image.
The username specified should be 'cloud-user' in case of CentOS 6.x image,
'centos' for CentOS 7 images and 'ubuntu' for Ubuntu images.

High Availability for HDFS and YARN
-----------------------------------
High Availability (Using the Quorum Journal Manager) can be
deployed automatically with the Ambari plugin. You can deploy High Available
cluster through UI by selecting ``NameNode HA`` and/or ``ResourceManager HA``
options in general configs of cluster template.

The NameNode High Availability is deployed using 2 NameNodes, one active and
one standby. The NameNodes use a set of JournalNodes and Zookepeer Servers to
ensure the necessary synchronization. In case of ResourceManager HA 2
ResourceManagers should be enabled in addition.

A typical Highly available Ambari cluster uses 2 separate NameNodes, 2 separate
ResourceManagers and at least 3 JournalNodes and at least 3 Zookeeper Servers.

HDP Version Support
-------------------
The HDP plugin currently supports deployment of HDP 2.3.

Cluster Validation
------------------
Prior to Hadoop cluster creation, the HDP plugin will perform the following
validation checks to ensure a successful Hadoop deployment:

* Ensure the existence of Ambari Server process in the cluster;
* Ensure the existence of a NameNode, Zookeeper, ResourceManagers processes
  HistoryServer and App TimeLine Server in the cluster

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
  ``http://tarballs.openstack.org/sahara/dist/``

* Sahara will create principals along with keytabs for system users
  like ``oozie``, ``hdfs`` and ``spark`` so that you will not have to
  perform additional auth operations to execute your jobs on top of the
  cluster.
