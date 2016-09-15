Requirements for Guests
=======================

Sahara manages guests of various platforms (for example Ubuntu, Fedora, RHEL,
and CentOS) with various versions of the Hadoop ecosystem projects installed.
There are common requirements for all guests, and additional requirements based
on the plugin that is used for cluster deployment.

Common Requirements
-------------------

* The operating system must be Linux
* cloud-init must be installed
* ssh-server must be installed

  + if a firewall is active it must allow connections on port 22 to enable ssh

Vanilla Plugin Requirements
---------------------------

If the Vanilla Plugin is used for cluster deployment the guest is required to
have

* ssh-client installed
* Java (version >= 6)
* Apache Hadoop installed
* 'hadoop' user created

See :doc:`hadoop-swift` for information on using Swift with your sahara cluster
(for EDP support Swift integration is currently required).

To support EDP, the following components must also be installed on the guest:

* Oozie version 4 or higher
* mysql
* hive

See :doc:`vanilla_imagebuilder` for instructions on building images for this
plugin.

Hortonworks Plugin Requirements
-------------------------------

This plugin does not have any additional requirements. Currently, only the
CentOS Linux and Ubuntu distributions are supported but other distributions
will be supported in the future.
To speed up provisioning, the HDP packages can be pre-installed on the image
used. The packages' versions depend on the HDP version being used.

Cloudera Plugin Requirements
----------------------------

Cloudera Plugin does not have any additional requirements, just build a CDH
image to deploy the cluster.

See :doc:`cdh_imagebuilder` for instructions on building images for this
plugin.
