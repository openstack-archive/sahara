Savanna Features
================

Cluster Scaling
---------------

The mechanism of cluster scaling is designed to enable user to change the number of running instances without creating a new cluster.

User may change number of instances in existing Node groups or even add any new Node Groups.

Cluster scaling requests are also validated as well as requests to create a cluster.

Currently only Vanilla plugin supports this feature.
If cluster cannot be scaled properly all changes will be rolled back.

Limitations
~~~~~~~~~~~

When user scales a Hadoop cluster using a reference plugin implementation (Vanilla plugin),
the cluster topology requested by user is verified for consistency as well as during cluster creation.

Currently there are the following limitations in cluster topology for Vanilla plugin:

* If namenode and jobtracker are on one node cluster cannot contain datanode or tasktracker running separately;
  We are planning to remove the restriction according https://blueprints.launchpad.net/savanna/+spec/get-rid-of-slaves-file

* Cluster should contain only one namenode and may contain only one jobtracker

* Cluster cannot be created if it contains processes without containing corresponding master-processes. E.g. it cannot
  contain tasktracker is there is no jobtracker


Swift support
-------------

If you want to work with swift, e.g. to run jobs on data located in swift or put jobs` result to swift, you need to use patched Hadoop and Swift.
For more info about this patching and configuring please see :doc:`hadoop-swift`. There are a lot of possible configs for swift which can be set but
currently Savanna automatically set information about swift filesystem implementation, location awarenass, url and tenant name for authorization in swift.
The only required information that is still needed to be set are username and password to access swift. So you need to explicitly specify this params during job running.

E.g. :

.. sourcecode:: bash

    hadoop distcp -D fs.swift.service.savanna.username=admin\
     -D fs.swift.service.savanna.password=swordfish\
      swift://integration.savanna/temp swift://integration.savanna/temp1

How to write swift path? The template is: ``swift://${container}.${provider}/${object}``.
We don't need to point out the account because it will be automatically
determined from tenant name from configs. Actually, account=tenant.

${provider} was designed to have an opportunity to work
with several swifts. E.g. theoretically possibly to read data from swift on one cloud and write it to another. In this case we need
to distinguish al least auth-properties rot them. But as for now Savanna automatically generates configs only for one provider (cloud)
and calls it "savanna".

Currently user has only an opportunity to say whether he or she wants to use swift on cluster or not. But there is a blueprint about making swift-access
more configurable during cluster creation for both REST API and UI: https://blueprints.launchpad.net/savanna/+spec/swift-configuration-through-rest-and-ui

Anti-affinity groups
--------------------
One of the problems in Hadoop running on OpenStack is that there is no ability to control where machine is actually running.
We cannot be sure that two new virtual machines are started on different hardware. So if cluster runs any replication processes
it is not reliable because all replicas may turn up on one hardware.
Anti-affinity groups feature provides an ability to explicitly tell Savanna to run specified processes on different compute nodes. This
is especially useful for Hadoop datanode-process to make HDFS replicas reliable.

