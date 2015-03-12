Cloudera Plugin
===============

The cloudera plugin is a Sahara plugin which allows the user to deploy and
operate a cluster with Cloudera Manager.

The cloudera plugin is enabled in Sahara by default. You can manually
modify the Sahara configuration file (default /etc/sahara/sahara.conf) to
explicitly enable or disable it in "plugins" line.

You need to build images using :doc:`cdh_imagebuilder` to produce images used
to provision cluster. They already have Cloudera Express installed (5.0.0 or
5.3.0 version).

The cloudera plugin requires an image to be tagged in Sahara Image Registry with
two tags: 'cdh' and '<cloudera version>' (e.g. '5' or '5.3.0').

The default username specified for these images is different for each
distribution:

+--------------+------------+
| OS           | username   |
+==============+============+
| Ubuntu 12.04 | ubuntu     |
+--------------+------------+
| CentOS 6.5   | cloud-user |
+--------------+------------+


Cluster Validation
------------------

When the user creates or scales a Hadoop cluster using a cloudera plugin, the
cluster topology requested by the user is verified for consistency.

The following limitations are required in the cluster topology for the cloudera
plugin:

  + Cluster must contain exactly one manager.
  + Cluster must contain exactly one namenode.
  + Cluster must contain exactly one secondarynamenode.
  + Cluster can contain at most one resourcemanager and this process is also
    required by nodemanager.
  + Cluster can contain at most one jobhistory and this process is also
    requried for resourcemanager.
  + Cluster can contain at most one oozie and this process is also required
    for EDP.
  + Cluster can't contain oozie without datanode.
  + Cluster can't contain oozie without nodemanager.
  + Cluster can't contain oozie without jobhistory.
