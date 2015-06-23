Vanilla Plugin
==============

The vanilla plugin is a reference implementation which allows users to operate
a cluster with Apache Hadoop.

For cluster provisioning prepared images should be used. They already have
Apache Hadoop 1.2.1 and Apache Hadoop 2.6.0 installed.

You may build images by yourself using :doc:`vanilla_imagebuilder` or you could
download prepared images from http://sahara-files.mirantis.com/images/upstream/kilo/

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

Known issue:

* Hive job has "KILLED" state after scaling cluster:
  https://bugs.launchpad.net/sahara/+bug/1413602

Cluster Validation
------------------

When user creates or scales a Hadoop cluster using a Vanilla plugin,
the cluster topology requested by user is verified for consistency.

Currently there are the following limitations in cluster topology for Vanilla
plugin:

For Vanilla Hadoop version 1.X.X:

  + Cluster must contain exactly one namenode
  + Cluster can contain at most one jobtracker
  + Cluster can contain at most one secondary namenode
  + Cluster can contain at most one oozie and this process is also required
    for EDP
  + Cluster can't contain oozie without jobtracker
  + Cluster can't have tasktracker nodes if it doesn't have jobtracker
  + Cluster can't have hive node if it doesn't have jobtracker.
  + Cluster can have at most one hive node.

For Vanilla Hadoop version 2.X.X:

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
