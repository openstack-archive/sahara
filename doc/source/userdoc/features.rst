Features Overview
=================

Cluster Scaling
---------------

The mechanism of cluster scaling is designed to enable user to change the number of running instances without creating a new cluster.
User may change number of instances in existing Node Groups or add new Node Groups.

If cluster fails to scale properly, all changes will be rolled back.

Currently only Vanilla plugin supports this feature. Visit :doc:`vanilla_plugin` for info about cluster topology limitations.

Swift Integration
-----------------

If you want to work with Swift, e.g. to run jobs on data located in Swift or put jobs` result into it, you need to use patched Hadoop and Swift.
For more info about this patching and configuring see :doc:`hadoop-swift`. There is a number of possible configs for Swift which can be set, but
currently Savanna automatically set information about swift filesystem implementation, location awareness, URL and tenant name for authorization.
The only required information that is still needed to be set are username and password to access Swift. So you need to explicitly specify these parameters while launching the job.

E.g. :

.. sourcecode:: console

    $ hadoop distcp -D fs.swift.service.savanna.username=admin \
     -D fs.swift.service.savanna.password=swordfish \
     swift://integration.savanna/temp swift://integration.savanna/temp1

How to compose a swift URL? The template is: ``swift://${container}.${provider}/${object}``.
We don't need to point out the account because it will be automatically
determined from tenant name from configs. Actually, account=tenant.

${provider} was designed to provide an opportunity to work
with several Swift installations. E.g. it is possible to read data from one Swift installation and write it to another one.
But as for now, Savanna automatically generates configs only for one Swift installation
with name "savanna".

Currently user can only enable/disable Swift for a Hadoop cluster. But there is a blueprint about making Swift access
more configurable: https://blueprints.launchpad.net/savanna/+spec/swift-configuration-through-rest-and-ui

Currently this feature is supported only by :doc:`vanilla_plugin`.

Cinder support
--------------
This feature is supported only by :doc:`vanilla_plugin`.

Cinder is a block storage service that can be used as an alternative for an ephemeral drive. Using Cinder volumes increases reliability of data which is important for HDFS service.

User can set how many volumes will be attached to each node in a Node Group and the size of each volume.

All volumes are attached during Cluster creation/scaling operations.

Neutron and Nova Network support
--------------------------------
OpenStack Cluster may use Nova Network or Neutron as a networking service. Savanna supports both, but when deployed,
a special configuration for networking should be set explicitly. By default Savanna will behave as if Nova Network is used.
If OpenStack Cluster uses Neutron, then ``use_neutron`` option should be set to ``True`` in Savanna configuration file.

.. sourcecode:: config

    use_neutron=True

Savanna Dashboard should also be configured properly to support Neutron. ``SAVANNA_USE_NEUTRON`` should be set to ``True`` in
OpenStack Dashboard ``local_settings.py`` configuration file.

.. sourcecode:: python

    SAVANNA_USE_NEUTRON=True


Floating IP Management
----------------------

Savanna needs to access instances through ssh during a Cluster setup. To establish a connection Savanna may
use both: fixed and floating IP of an Instance. By default ``use_floating_ips`` parameter is set to ``True``, so
Savanna will use Floating IP of an Instance to connect. In this case, user has two options for how to make all instances
get a floating IP:

* Nova Network may be configured to assign floating IPs automatically by setting ``auto_assign_floating_ip`` to ``True`` in ``nova.conf``
* User may specify a floating IP pool for each Node Group directly.

Note: When using floating IPs for management (``use_floating_ip=True``) **every** instance in the Cluster should have a floating IP,
otherwise Savanna will not be able to work with it.

If ``use_floating_ips`` parameter is set to ``False`` Savanna will use Instances' fixed IPs for management. In this case
the node where Savanna is running should have access to Instances' fixed IP network. When OpenStack uses Neutron for
networking, user will be able to choose fixed IP network for all instances in a Cluster.

Anti-affinity
-------------
One of the problems in Hadoop running on OpenStack is that there is no ability to control where machine is actually running.
We cannot be sure that two new virtual machines are started on different physical machines. As a result, any replication with cluster
is not reliable because all replicas may turn up on one physical machine.
Anti-affinity feature provides an ability to explicitly tell Savanna to run specified processes on different compute nodes. This
is especially useful for Hadoop datanode process to make HDFS replicas reliable.

That feature requires certain adjustments on Nova side to work.
See :doc:`anti_affinity` for details.

This feature is supported by all plugins out of the box.
