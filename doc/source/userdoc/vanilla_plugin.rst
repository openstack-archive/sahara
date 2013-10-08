Vanilla Plugin
==============

Vanilla plugin is a reference plugin implementation which allows to operate with cluster with Apache Hadoop.

For cluster provisioning prepared images should be used. They already have Apache Hadoop 1.2.1 installed.
Here you can find prepared images:

* http://savanna-files.mirantis.com/savanna-0.3-vanilla-1.2.1-ubuntu-13.04.qcow2
* http://savanna-files.mirantis.com/savanna-0.3-vanilla-1.2.1-fedora-19.qcow2

Besides, you may build images by yourself using :doc:`diskimagebuilder`.
Keep in mind that if you want to use "Swift Integration" feature ( :doc:`features`),
Hadoop must be patched with implementation of Swift File System.
For more information about patching required by "Swift Integration" feature see :doc:`hadoop-swift`.

Vanilla plugin requires an image to be tagged in Savanna Image Registry with
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

* If namenode and jobtracker are on one the same machine, all cluster workers must run both datanode and tasktracker
  We are planning to remove the restriction according https://blueprints.launchpad.net/savanna/+spec/get-rid-of-slaves-file

* Cluster should contain only one namenode and only one jobtracker

* Cluster cannot be created if it contains worker processes without containing corresponding master processes. E.g. it cannot
  contain tasktracker if there is no jobtracker
