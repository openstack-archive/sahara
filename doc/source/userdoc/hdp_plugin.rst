
Hortonworks Data Plaform Plugin
===============================
The Hortonworks Data Platform (HDP) Sahara plugin provides a way to provision HDP clusters on OpenStack using templates in a single click and in an easily repeatable fashion. As seen from the architecture diagram below, the Sahara controller serves as the glue between Hadoop and OpenStack. The HDP plugin mediates between the Sahara controller and Apache Ambari in order to deploy and configure Hadoop on OpenStack. Core to the HDP Plugin is Apache Ambari that is used as the orchestrator for deploying the HDP stack on OpenStack.

.. image:: ../images/hdp-plugin-architecture.png
    :width: 800 px
    :scale: 80 %
    :align: center

The HDP plugin uses Ambari Blueprints aka templates for cluster provisioning.

Apache Ambari Blueprints (aka Cluster templates)
------------------------------------------------
Apache Ambari Blueprints is a portable document definition, which provides a complete definition for an Apache Hadoop cluster, including cluster topology, components, services and their configurations. Ambari Blueprints can be consumed by the HDP plugin to instantiate a Hadoop cluster on OpenStack. The benefits of this approach is that it allows for Hadoop clusters to be configured and deployed using an Ambari native format that can be used with as well as outside of OpenStack allowing for clusters to be re-instantiated in a variety of environments.
 
For more information about Apache Ambari Blueprints, refer to: https://issues.apache.org/jira/browse/AMBARI-1783. Note that Apache Ambari Blueprints are not yet finalized.

Operation
---------
The HDP Plugin performs the following four primary functions during cluster creation:

1. Software deployment - the plugin orchestrates the deployment of the required software to the target VMs
2. Services Installation - the Hadoop services configured for the node groups within the cluster are installed on the associated VMs
3. Services Configuration - the plugin merges the default configuration values and user provided configurations for each installed service to the cluster
4. Services Start - the plugin invokes the appropriate APIs to indicate to the Ambari Server that the cluster services should be started

Images
------
The Sahara HDP plugin can make use of either minimal (operating system only) images or pre-populated HDP images. The base requirement for both is that the image is cloud-init enabled and contains a supported operating system (see http://docs.hortonworks.com/HDPDocuments/HDP1/HDP-1.2.4/bk_hdp1-system-admin-guide/content/sysadminguides_ha_chap2_3.html).
 
The advantage of a pre-populated image is that provisioning time is accelerated, as packages do not need to be downloaded and installed which make up the majority of the time spent in the provisioning cycle.
 
As with the provided pre-populated image, a pre-populated image can install any of the following packages:
 
* hadoop-libhdfs
* hadoop-native
* hadoop-pipes
* hadoop-sbin
* hadoop-lzo
* hadoop-lzo-native
* mysql-server
* httpd
* net-snmp
* net-snmp-utils
* perl-Net-SNMP
* nagios
* fping
* nagios-plugins
* hdp_mon_nagios_addons
* ganglia-gmetad
* gweb hdp_mon_ganglia_addons
* ganglia-gmond
* python-rrdtool.x86_64
* glibc glibc.i686
* appropriate JDK satisfying Ambari requirement
* epel-release
 
Any packages that are not installed in a pre-populated image will automatically be installed during the HDP provisioning process.
There are two VM images provided for use with the HDP Plugin:

1. `centos-6_64-hdp-1.3.qcow2 <http://public-repo-1.hortonworks.com/savanna/images/centos-6_4-64-hdp-1.3.qcow2>`_: This image contains most of the requisite packages necessary for HDP deployment. The packages contained herein correspond to the HDP 1.3 release. The operating system is a minimal CentOS 6.4 cloud-init enabled install. This image can only be used to provision HDP 1.3 hadoop clusters.
2. `centos-6-64-hdp-vanilla.qcow2 <http://public-repo-1.hortonworks.com/savanna/images/centos-6_4-64-vanilla.qcow2>`_: This image provides only a minimal install of CentOS 6.4  and is cloud-init enabled. This image can be used to provision any versions of HDP supported by Sahara.

HDP plugin requires an image to be tagged in Sahara Image Registry with
two tags: 'hdp' and '<hdp version>' (e.g. '1.3.2').

Also in the Image Registry you will need to specify username for an image.
It should be 'root' for both images.
 
Please refer to the reference VM image provided for specific details.

Limitations
-----------
The HDP plugin currently has the following limitations:

* Currently, the HDP plugin provides support for HDP 1.3. Once HDP2 is released, support for this version will be provided.
* Swift integration is not yet implemented.
* It is not possible to decrement the number of node-groups or hosts per node group in a Sahara generated cluster.
* Only the following services are available to be deployed via Sahara:
      * Ambari
      * Nagios
      * Ganglia
      * HDFS
      * MAPREDUCE

Note: Other services may be added using Ambari after initial cluster creation.

Cluster Validation
------------------
Prior to Hadoop cluster creation, the HDP plugin will perform the following validation checks to ensure a successful Hadoop deployment:

* Ensure the existence of a NAMENODE process in the cluster
* Ensure the existence of a JOBTRACKER should any TASKTRACKER be deployed to the cluster
* Ensure the deployment of one Ambari Server instance to the cluster
* Ensure that each defined node group had an associated Ambari Agent configured

The HDP Plugin and Sahara Support
----------------------------------
A Hortonworks supported version of HDP OpenStack plugin will become available at a future date. For more information, please contact Hortonworks. 
