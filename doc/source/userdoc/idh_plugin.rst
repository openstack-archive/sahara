Intel Distribution for Apache Hadoop Plugin
===========================================

The Intel Distribution for Apache Hadoop (IDH) Sahara plugin provides a way
to provision IDH clusters on OpenStack using templates in a single click and
in an easily repeatable fashion. The Sahara controller serves as the glue
between Hadoop and OpenStack. The IDH plugin mediates between the Sahara
controller and Intel Manager in order to deploy and configure Hadoop on
OpenStack. Intel Manager is used as the orchestrator for deploying the IDH
stack on OpenStack.

For cluster provisioning images supporting cloud init should be used. The only
supported operation system for now is Cent OS 6.4. Here you can find the image:

* http://sahara-files.mirantis.com/CentOS-6.4-cloud-init.qcow2

IDH plugin requires an image to be tagged in Sahara Image Registry with
two tags: 'idh' and '<IDH version>' (e.g. '2.5.1').

Also you should specify a default username of "cloud-user" to be used in the
Image.

Limitations
-----------
The IDH plugin currently has the following limitations:

* IDH plugin downloads the Intel Manager package from a URL provided in the
  cluster configuration. A local HTTP mirror should be used in cases where the
  VMs do not have access to the Internet or have port limitations.
* IDH plugin adds the Intel rpm repository to the yum configuration. The
  repository URL can be chosen during Sahara cluster configuration. A local
  mirror should be used in cases where the VMs have no access to the Internet
  or have port limitations. Refer to the IDH documentation for instructions on
  how to create a local mirror.
* Hadoop cluster scaling is supported only for datanode and tasktracker
  (nodemanager for IDH 3.x) processes.

Cluster Validation
------------------
When a user creates or scales a Hadoop cluster using the IDH plugin, the
cluster topology requested by the user is verified for consistency.

Currently there are the following limitations in cluster topology for IDH plugin:

* Cluster should contain
    * exactly one manager
    * exactly one namenode
    * at most one jobtracker for IDH 2.x or resourcemanager for IDH 3.x
    * at most one oozie

* Cluster cannot be created if it contains worker processes without containing
  corresponding master processes. E.g. it cannot contain tasktracker if there
  is no jobtracker.
