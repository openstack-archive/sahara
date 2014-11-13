Vanilla Plugin
==============

The vanilla plugin is a reference implementation which allows users to operate
a cluster with Apache Hadoop.

For cluster provisioning prepared images should be used. They already have
Apache Hadoop 1.2.1 and Apache Hadoop 2.4.1 installed. Prepared images
can be found at the following locations:

* http://sahara-files.mirantis.com/sahara-juno-vanilla-1.2.1-ubuntu-14.04.qcow2
* http://sahara-files.mirantis.com/sahara-juno-vanilla-1.2.1-centos-6.5.qcow2
* http://sahara-files.mirantis.com/sahara-juno-vanilla-1.2.1-fedora-20.qcow2

* http://sahara-files.mirantis.com/sahara-juno-vanilla-2.4.1-ubuntu-14.04.qcow2
* http://sahara-files.mirantis.com/sahara-juno-vanilla-2.4.1-centos-6.5.qcow2
* http://sahara-files.mirantis.com/sahara-juno-vanilla-2.4.1-fedora-20.qcow2

Additionally, you may build images by yourself using :doc:`diskimagebuilder`.
Keep in mind that if you want to use the Swift Integration feature
( :doc:`features`),
Hadoop 1.2.1 must be patched with an implementation of Swift File System.
For more information about patching required by the Swift Integration feature
see :doc:`hadoop-swift`.

Vanilla plugin requires an image to be tagged in Sahara Image Registry with
two tags: 'vanilla' and '<hadoop version>' (e.g. '1.2.1').

The default username specified for these images is different
for each distribution:

+--------------+------------+
| OS           | username   |
+==============+============+
| Ubuntu 14.04 | ubuntu     |
+--------------+------------+
| Fedora 20    | fedora     |
+--------------+------------+
| CentOS 6.5   | cloud-user |
+--------------+------------+


Cluster Validation
------------------

When user creates or scales a Hadoop cluster using a Vanilla plugin,
the cluster topology requested by user is verified for consistency.

Currently there are the following limitations in cluster topology for Vanilla
plugin:

For Vanilla Hadoop version 1.X.X:

  + Cluster must contain exactly one namenode
  + Cluster can contain at most one jobtracker
  + Cluster can contain at most one oozie and this process is also required
    for EDP
  + Cluster can't contain oozie without jobtracker
  + Cluster can't have tasktracker nodes if it doesn't have jobtracker

For Vanilla Hadoop version 2.X.X:

  + Cluster must contain exactly one namenode
  + Cluster can contain at most one resourcemanager
  + Cluster can contain at most one historyserver
  + Cluster can contain at most one oozie and this process is also required
    for EDP
  + Cluster can't contain oozie without resourcemanager and without
    historyserver
  + Cluster can't have nodemanager nodes if it doesn't have resourcemanager
