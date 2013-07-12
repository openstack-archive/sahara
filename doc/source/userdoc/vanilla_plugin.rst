Vanilla Plugin
==============

Vanilla plugin is a reference plugin implementation which allows to operate with cluster with Apache Hadoop 1.1.2.

For cluster provisioning prepared images should be used. They already have Apache Hadoop 1.1.2 installed.
Here you can find prepared images:

* http://savanna-files.mirantis.com/savanna-0.2-vanilla-1.1.2-ubuntu-12.10.qcow2
* http://savanna-files.mirantis.com/savanna-0.2-vanilla-1.1.2-fedora-18.qcow2

Besides, you may build images by yourself using :doc:`diskimagebuilder`.
But please keep in mind that if you want to use "Swift support" feature ( :doc:`features`) you need to include hadoop patch to image.
For more information about patching required by  "Swift support" feature visit :doc:`hadoop-swift`.


Limitations
-----------

When user creates or scales a Hadoop cluster using a reference plugin implementation (Vanilla plugin),
the cluster topology requested by user is verified for consistency.

Currently there are the following limitations in cluster topology for Vanilla plugin:

* If namenode and jobtracker are on one node cluster cannot contain datanode or tasktracker running separately;
  We are planning to remove the restriction according https://blueprints.launchpad.net/savanna/+spec/get-rid-of-slaves-file

* Cluster should contain only one namenode and may contain only one jobtracker

* Cluster cannot be created if it contains processes without containing corresponding master-processes. E.g. it cannot
  contain tasktracker is there is no jobtracker
