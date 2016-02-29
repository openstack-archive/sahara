MapR Distribution Plugin
========================
The MapR Sahara plugin allows to provision MapR clusters on
OpenStack in an easy way and do it, quickly, conveniently and simply.

Operation
---------
The MapR Plugin performs the following four primary functions during cluster
creation:

1. MapR components deployment - the plugin manages the deployment of the
   required software to the target VMs
2. Services Installation - MapR services are installed according to provided
   roles list
3. Services Configuration - the plugin combines default settings with user
   provided settings
4. Services Start - the plugin starts appropriate services according to
   specified roles

Images
------
The Sahara MapR plugin can make use of either minimal (operating system only)
images or pre-populated MapR images. The base requirement for both is that the
image is cloud-init enabled and contains a supported operating system (see
http://doc.mapr.com/display/MapR/OS+Support+Matrix).

The advantage of a pre-populated image is that provisioning time is reduced, as
packages do not need to be downloaded which make up the majority of the time
spent in the provisioning cycle. In addition, provisioning large clusters will
put a burden on the network as packages for all nodes need to be downloaded
from the package repository.

For more information about MapR images, refer to
https://github.com/openstack/sahara-image-elements.

There are eight VM images provided for use with the MapR Plugin, that can also
be built using the tools available in sahara-image-elements:

* https://s3-us-west-2.amazonaws.com/sahara-images/ubuntu_trusty_mapr_plain_latest.qcow2
* https://s3-us-west-2.amazonaws.com/sahara-images/centos_6.5_mapr_plain_latest.qcow2
* https://s3-us-west-2.amazonaws.com/sahara-images/ubuntu_trusty_mapr_5.0.0_latest.qcow2
* https://s3-us-west-2.amazonaws.com/sahara-images/centos_6.5_mapr_5.0.0_latest.qcow2

MapR plugin needs an image to be tagged in Sahara Image Registry with
two tags: 'mapr' and '<MapR version>' (e.g. '5.0.0.mrv2').


The default username specified for these images is different for each
distribution:

+--------------+------------+
| OS           | username   |
+==============+============+
| Ubuntu 14.04 | ubuntu     |
+--------------+------------+
| CentOS 6.5   | cloud-user |
+--------------+------------+


Hadoop Version Support
----------------------
The MapR plugin currently supports Hadoop 2.7.0 (5.0.0.mrv2).

Cluster Validation
------------------
When the user creates or scales a Hadoop cluster using a mapr plugin, the
cluster topology requested by the user is verified for consistency.

Every MapR cluster must contain:

* at least 1 *CLDB* process
* exactly 1 *Webserver* process
* odd number of *ZooKeeper* processes but not less than 1
* *FileServer* process on every node
* at least 1 Cinder volume or ephemeral drive per instance

Every Hadoop cluster must contain exactly 1 *Oozie* process

Every MapReduce v1 cluster must contain:

* at least 1 *JobTracker* process
* at least 1 *TaskTracker* process

Every MapReduce v2 cluster must contain:

* exactly 1 *ResourceManager* process
* exactly 1 *HistoryServer* process
* at least 1 *NodeManager* process

Every Spark cluster must contain:

* exactly 1 *Spark Master* process
* exactly 1 *Spark HistoryServer* process
* at least 1 *Spark Slave* (worker) process

HBase service is considered valid if:

* cluster has at least 1 *HBase-Master* process
* cluster has at least 1 *HBase-RegionServer* process

Hive service is considered valid if:

* cluster has exactly 1 *HiveMetastore* process
* cluster has exactly 1 *HiveServer2* process

Hue service is considered valid if:

* cluster has exactly 1 *Hue* process
* *Hue* process resides on the same node as *HttpFS* process

HttpFS service is considered valid if cluster has exactly 1 *HttpFS* process

Sqoop service is considered valid if cluster has exactly 1 *Sqoop2-Server*
process

The MapR Plugin
---------------
For more information, please contact MapR.
