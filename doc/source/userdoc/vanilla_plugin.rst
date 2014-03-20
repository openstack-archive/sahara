Vanilla Plugin
==============

Vanilla plugin is a reference plugin implementation which allows to operate with cluster with Apache Hadoop.

For cluster provisioning prepared images should be used. They already have Apache Hadoop 1.2.1 installed.
Here you can find prepared images:

* http://sahara-files.mirantis.com/savanna-icehouse-vanilla-1.2.1-ubuntu-13.10.qcow2
* http://sahara-files.mirantis.com/savanna-icehouse-vanilla-1.2.1-fedora-19.qcow2
* http://sahara-files.mirantis.com/savanna-icehouse-vanilla-1.2.1-centos-6.4.qcow2

Besides, you may build images by yourself using :doc:`diskimagebuilder`.
Keep in mind that if you want to use "Swift Integration" feature ( :doc:`features`),
Hadoop must be patched with implementation of Swift File System.
For more information about patching required by "Swift Integration" feature see :doc:`hadoop-swift`.

Vanilla plugin requires an image to be tagged in Sahara Image Registry with
two tags: 'vanilla' and '<hadoop version>' (e.g. '1.2.1').

Also you should specify username of default cloud-user used in the Image:

+--------------+------------+
| OS           | username   |
+==============+============+
| Ubuntu 13.04 | ubuntu     |
+--------------+------------+
| Fedora 19    | fedora     |
+--------------+------------+
| CentOS 6.4   | cloud-user |
+--------------+------------+


Limitations
-----------

When user creates or scales a Hadoop cluster using a Vanilla plugin,
the cluster topology requested by user is verified for consistency.

Currently there are the following limitations in cluster topology for Vanilla plugin:

* Cluster should contain
    * exactly one namenode
    * at most one jobtracker
    * at most one oozie

* Cluster cannot be created if it contains worker processes without containing corresponding master processes. E.g. it cannot
  contain tasktracker if there is no jobtracker
