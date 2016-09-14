Vanilla Plugin
==============

The vanilla plugin is a reference implementation which allows users to operate
a cluster with Apache Hadoop.

Since the Newton release Spark is integrated into the Vanilla plugin so you
can launch Spark jobs on a Vanilla cluster.

For cluster provisioning prepared images should be used. They already have
Apache Hadoop 2.7.1 installed.

You may build images by yourself using :doc:`vanilla_imagebuilder` or you could
download prepared images from http://sahara-files.mirantis.com/images/upstream

Vanilla plugin requires an image to be tagged in Sahara Image Registry with
two tags: 'vanilla' and '<hadoop version>' (e.g. '2.7.1').

The default username specified for these images is different
for each distribution:

+--------------+------------+
| OS           | username   |
+==============+============+
| Ubuntu 14    | ubuntu     |
+--------------+------------+
| Fedora 20    | fedora     |
+--------------+------------+
| CentOS 6     | cloud-user |
+--------------+------------+
| CentOS 7     | centos     |
+--------------+------------+

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
