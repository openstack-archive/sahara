MapR Distribution Plugin
========================

The MapR Sahara plugin allows to provision MapR clusters on
OpenStack in an easy way and do it, quickly, conveniently and simply.


Operation
---------

The MapR Plugin performs the following four primary functions during cluster creation:

1. MapR components deployment - the plugin manages the deployment of the required software to the target VMs
2. Services Installation - MapR services are installed according to provided roles list
3. Services Configuration - the plugin combines default settings with user provided settings
4. Services Start - the plugin starts appropriate services according to specified roles

Images
------

For cluster provisioning prepared images should be used. They already have
MapR 3.1.1 (with Apache Hadoop 0.20.2) and MapR 4.0.1 (with Apache Hadoop 2.4.1) installed.


MapR plugin needs an image to be tagged in Sahara Image Registry with
two tags: 'MapR' and '<MapR version>' (e.g. '4.0.1').

Note that you should provide username of default cloud-user used in the Image:

+--------------+------------+
| OS           | username   |
+==============+============+
| Ubuntu 14.04 | ubuntu     |
+--------------+------------+
| CentOS 6.5   | cloud-user |
+--------------+------------+


Hadoop Version Support
----------------------
The MapR plugin currently supports Hadoop 0.20.2 and Hadoop 2.4.1.

Cluster Validation
------------------

Mr1 Cluster is valid if and only if:

1. Zookeeper component count per cluster equals 1 or greater.  Zookeeper service is up and running.

    2.1 Each node has Fileserver component.  Fileserver is up and running on each node. Or
    2.2 Each node has NFS server component. NFS server is up and running.

3. If node has TaskTracker component then  Fileserver must be also.
4. Web-server component  count per cluster equals 0 or 1.  Web-server is up and running.


YARN Cluster is valid if and only if:

1. Zookeeper component count per cluster equals 1 or greater.  Zookeeper service is up and running.
2.  Resource manager component count per cluster equals 1 or greater.  Resource manager component is up and running.

    3.1 Each node has Fileserver component.  Fileserver is up and running on each node. Or
    3.2 Each node has NFS server component. NFS server is up and running.

4. Web-server component  count per cluster equals 0 or 1.  Web-server is up and running.
5. History server component count per cluster equals 1.  History server  is up and running.


The MapR Plugin
---------------
For more information, please contact MapR.
