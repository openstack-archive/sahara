Vanilla Plugin
==============

Vanilla plugin is a reference plugin implementation which allows to operate with cluster with Apache Hadoop.

For cluster provisioning prepared images should be used. They already have
Apache Hadoop 1.2.1 and Apache Hadoop 2.3.0 installed. Here you can find
prepared images:

* http://sahara-files.mirantis.com/sahara-icehouse-vanilla-1.2.1-ubuntu-13.10.qcow2
* http://sahara-files.mirantis.com/sahara-icehouse-vanilla-1.2.1-fedora-20.qcow2
* http://sahara-files.mirantis.com/sahara-icehouse-vanilla-1.2.1-centos-6.5.qcow2

* http://sahara-files.mirantis.com/sahara-icehouse-vanilla-2.3.0-ubuntu-13.10.qcow2
* http://sahara-files.mirantis.com/sahara-icehouse-vanilla-2.3.0-fedora-20.qcow2
* http://sahara-files.mirantis.com/sahara-icehouse-vanilla-2.3.0-centos-6.5.qcow2

Besides, you may build images by yourself using :doc:`diskimagebuilder`.
Keep in mind that if you want to use "Swift Integration" feature ( :doc:`features`),
Hadoop 1.2.1 must be patched with implementation of Swift File System.
For more information about patching required by "Swift Integration" feature see :doc:`hadoop-swift`.

Vanilla plugin requires an image to be tagged in Sahara Image Registry with
two tags: 'vanilla' and '<hadoop version>' (e.g. '1.2.1').

Also you should specify username of default cloud-user used in the Image:

+--------------+------------+
| OS           | username   |
+==============+============+
| Ubuntu 13.10 | ubuntu     |
+--------------+------------+
| Fedora 20    | fedora     |
+--------------+------------+
| CentOS 6.5   | cloud-user |
+--------------+------------+


Cluster Validation
------------------

When user creates or scales a Hadoop cluster using a Vanilla plugin,
the cluster topology requested by user is verified for consistency.

Currently there are the following limitations in cluster topology for Vanilla plugin:

For Vanilla Hadoop version 1.X.X:

  + Cluster must contain exactly one namenode
  + Cluster can contain at most one jobtracker
  + Cluster can contain at most one oozie and this process is also required for EDP
  + Cluster can't contain oozie without jobtraker
  + Cluster can't have tasktracker nodes if it doesn't have jobtracker

For Vanilla Hadoop version 2.X.X:

  + Cluster must contain exactly one namenode
  + Cluster can contain at most one resourcemanager
  + Cluster can contain at most one historyserver
  + Cluster can contain at most one oozie and this process is also required for EDP
  + Cluster can't contain oozie without resourcemanager and without historyserver
  + Cluster can't have nodemanager nodes if it doesn't have resourcemanager

