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
currently Sahara automatically set information about swift filesystem implementation, location awareness, URL and tenant name for authorization.
The only required information that is still needed to be set are username and password to access Swift. So you need to explicitly specify these parameters while launching the job.

E.g. :

.. sourcecode:: console

    $ hadoop distcp -D fs.swift.service.sahara.username=admin \
     -D fs.swift.service.sahara.password=swordfish \
     swift://integration.sahara/temp swift://integration.sahara/temp1

How to compose a swift URL? The template is: ``swift://${container}.${provider}/${object}``.
We don't need to point out the account because it will be automatically
determined from tenant name from configs. Actually, account=tenant.

${provider} was designed to provide an opportunity to work
with several Swift installations. E.g. it is possible to read data from one Swift installation and write it to another one.
But as for now, Sahara automatically generates configs only for one Swift installation
with name "sahara".

Currently user can only enable/disable Swift for a Hadoop cluster. But there is a blueprint about making Swift access
more configurable: https://blueprints.launchpad.net/sahara/+spec/swift-configuration-through-rest-and-ui

Currently this feature is supported only by :doc:`vanilla_plugin`.

Cinder support
--------------
This feature is supported only by :doc:`vanilla_plugin`.

Cinder is a block storage service that can be used as an alternative for an ephemeral drive. Using Cinder volumes increases reliability of data which is important for HDFS service.

User can set how many volumes will be attached to each node in a Node Group and the size of each volume.

All volumes are attached during Cluster creation/scaling operations.

Neutron and Nova Network support
--------------------------------
OpenStack Cluster may use Nova Network or Neutron as a networking service. Sahara supports both, but when deployed,
a special configuration for networking should be set explicitly. By default Sahara will behave as if Nova Network is used.
If OpenStack Cluster uses Neutron, then ``use_neutron`` option should be set to ``True`` in Sahara configuration file.  In
addition, if the OpenStack Cluster supports network namespaces, set the ``use_namespaces`` option to ``True``

.. sourcecode:: cfg

    use_neutron=True
    use_namespaces=True

Sahara Dashboard should also be configured properly to support Neutron. ``SAHARA_USE_NEUTRON`` should be set to ``True`` in
OpenStack Dashboard ``local_settings.py`` configuration file.

.. sourcecode:: python

    SAHARA_USE_NEUTRON=True


Floating IP Management
----------------------

Sahara needs to access instances through ssh during a Cluster setup. To establish a connection Sahara may
use both: fixed and floating IP of an Instance. By default ``use_floating_ips`` parameter is set to ``True``, so
Sahara will use Floating IP of an Instance to connect. In this case, user has two options for how to make all instances
get a floating IP:

* Nova Network may be configured to assign floating IPs automatically by setting ``auto_assign_floating_ip`` to ``True`` in ``nova.conf``
* User may specify a floating IP pool for each Node Group directly.

Note: When using floating IPs for management (``use_floating_ip=True``) **every** instance in the Cluster should have a floating IP,
otherwise Sahara will not be able to work with it.

If ``use_floating_ips`` parameter is set to ``False`` Sahara will use Instances' fixed IPs for management. In this case
the node where Sahara is running should have access to Instances' fixed IP network. When OpenStack uses Neutron for
networking, user will be able to choose fixed IP network for all instances in a Cluster.

Anti-affinity
-------------
One of the problems in Hadoop running on OpenStack is that there is no ability to control where machine is actually running.
We cannot be sure that two new virtual machines are started on different physical machines. As a result, any replication with cluster
is not reliable because all replicas may turn up on one physical machine.
Anti-affinity feature provides an ability to explicitly tell Sahara to run specified processes on different compute nodes. This
is especially useful for Hadoop datanode process to make HDFS replicas reliable.

.. _`enable-anti-affinity`:

The Anti-Affinity feature requires certain scheduler filters to be enabled on Nova.
Edit your ``/etc/nova/nova.conf`` in the following way:

.. sourcecode:: cfg

    [DEFAULT]

    ...

    scheduler_driver=nova.scheduler.filter_scheduler.FilterScheduler
    scheduler_default_filters=DifferentHostFilter,SameHostFilter

This feature is supported by all plugins out of the box.

Data-locality
-------------
This feature is supported only by :doc:`vanilla_plugin`.

It is extremely important for data processing to do locally (on the same rack,
openstack compute node or even VM) as much work as
possible. Hadoop supports data-locality feature and can schedule jobs to
tasktracker nodes that are local for input stream. In this case tasktracker
could communicate directly with local data node.

Sahara supports topology configuration for HDFS and Swift data sources.

To enable data-locality set ``enable_data_locality`` parameter to ``True`` in
Sahara configuration file

.. sourcecode:: cfg

    enable_data_locality=True

In this case two files with topology must be provided to Sahara.
Options ``compute_topology_file`` and ``swift_topology_file`` parameters
control location of files with compute and swift nodes topology descriptions
correspondingly.

``compute_topology_file`` should contain mapping between compute nodes and
racks in the following format:

.. sourcecode:: cfg

    compute1 /rack1
    compute1 /rack2
    compute1 /rack2

Note that compute node name must be exactly the same as configured in
openstack (``host`` column in admin list for instances).

``swift_topology_file`` should contain mapping between swift nodes and
racks in the following format:

.. sourcecode:: cfg

    node1 /rack1
    node2 /rack2
    node3 /rack2

Note that swift node must be exactly the same as configures in object.builder
swift ring. Also make sure that VMs with tasktracker service has direct access
to swift nodes.

Hadoop versions after 1.2.0 support four-layer topology
(https://issues.apache.org/jira/browse/HADOOP-8468). To enable this feature
set ``enable_hypervisor_awareness`` option to ``True`` in Sahara configuration
file. In this case Sahara will add compute node ID as a second level of
topology for Virtual Machines.

Heat Integration
----------------

Sahara may use `OpenStack Orchestration engine <https://wiki.openstack.org/wiki/Heat>`_ (aka Heat) to provision nodes for Hadoop cluster.
To make Sahara work with Heat the following steps are required:

* Your OpenStack installation must have 'orchestration' service up and running
* Sahara must contain the following configuration parameter in *sahara.conf*:

.. sourcecode:: cfg

    # An engine which will be used to provision infrastructure for Hadoop cluster. (string value)
    infrastructure_engine=heat


The following features are supported in the new Heat engine:

+-----------------------------------------+-------------------------+-----------------------------------------+
| Feature                                 | Heat engine             | Known issues                            |
+=========================================+=========================+=========================================+
| Vanilla plugin provisioning             | Implemented             |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| HDP plugin provisioning                 | Implemented             |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| IDH plugin provisioning                 | Implemented             |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Cluster scaling                         | Implemented             |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Cluster rollback                        | Implemented             |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Volumes attachments                     | Implemented             |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Hadoop and Swift integration            | Not affected            |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Anti-affinity                           | Implemented             | https://launchpad.net/bugs/1268610      |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Floating IP Management                  | Implemented             |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Neutron support                         | Implemented             |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Nova Network support                    | TBD                     | https://launchpad.net/bugs/1259176      |
+-----------------------------------------+-------------------------+-----------------------------------------+
| Elastic Data Processing                 | Not affected            |                                         |
+-----------------------------------------+-------------------------+-----------------------------------------+
