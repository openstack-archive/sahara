Features Overview
=================

Cluster Scaling
---------------

The mechanism of cluster scaling is designed to enable a user to change the
number of running instances without creating a new cluster.
A user may change the number of instances in existing Node Groups or add new Node
Groups.

If a cluster fails to scale properly, all changes will be rolled back.

Swift Integration
-----------------

In order to leverage Swift within Hadoop, including using Swift data sources
from within EDP, Hadoop requires the application of a patch.
For additional information about using Swift with Sahara, including patching
Hadoop and configuring Sahara, please refer to the :doc:`hadoop-swift`
documentation.

Cinder support
--------------
Cinder is a block storage service that can be used as an alternative for an
ephemeral drive. Using Cinder volumes increases reliability of data which is
important for HDFS service.

A user can set how many volumes will be attached to each node in a Node Group
and the size of each volume.

All volumes are attached during Cluster creation/scaling operations.

.. _neutron-nova-network:

Neutron and Nova Network support
--------------------------------
OpenStack clusters may use Nova or Neutron as a networking service. Sahara
supports both, but when deployed a special configuration for networking
should be set explicitly. By default Sahara will behave as if Nova is used.
If an OpenStack cluster uses Neutron, then the ``use_neutron`` property should
be set to ``True`` in the Sahara configuration file. Additionally, if the
cluster supports network namespaces the ``use_namespaces`` property can be
used to enable their usage.

.. sourcecode:: cfg

    [DEFAULT]
    use_neutron=True
    use_namespaces=True

.. note::
    If a user other than ``root`` will be running the Sahara server
    instance and namespaces are used, some additional configuration is
    required, please see the :doc:`advanced.configuration.guide` for more
    information.

Floating IP Management
----------------------

Sahara needs to access instances through ssh during a Cluster setup. To
establish a connection Sahara may
use both: fixed and floating IP of an Instance. By default
``use_floating_ips`` parameter is set to ``True``, so
Sahara will use Floating IP of an Instance to connect. In this case, the user has
two options for how to make all instances
get a floating IP:

* Nova Network may be configured to assign floating IPs automatically by
  setting ``auto_assign_floating_ip`` to ``True`` in ``nova.conf``
* User may specify a floating IP pool for each Node Group directly.

Note: When using floating IPs for management (``use_floating_ip=True``)
**every** instance in the Cluster should have a floating IP,
otherwise Sahara will not be able to work with it.

If the ``use_floating_ips`` parameter is set to ``False`` Sahara will use
Instances' fixed IPs for management. In this case
the node where Sahara is running should have access to Instances' fixed IP
network. When OpenStack uses Neutron for
networking, a user will be able to choose fixed IP network for all instances
in a Cluster.

Anti-affinity
-------------
One of the problems in Hadoop running on OpenStack is that there is no
ability to control where the machine is actually running.
We cannot be sure that two new virtual machines are started on different
physical machines. As a result, any replication with the cluster
is not reliable because all replicas may turn up on one physical machine.
The anti-affinity feature provides an ability to explicitly tell Sahara to run
specified processes on different compute nodes. This
is especially useful for the Hadoop data node process to make HDFS replicas
reliable.

Starting with the Juno release, Sahara creates server groups with the
``anti-affinity`` policy to enable the anti-affinity feature. Sahara creates one
server group per cluster and assigns all instances with affected processes to
this server group. Refer to the Nova documentation on how server groups work.

This feature is supported by all plugins out of the box.

Data-locality
-------------
It is extremely important for data processing to work locally (on the same rack,
OpenStack compute node or even VM). Hadoop supports the data-locality feature and can schedule jobs to
task tracker nodes that are local for input stream. In this case task tracker
could communicate directly with the local data node.

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

Note that the compute node name must be exactly the same as configured in
OpenStack (``host`` column in admin list for instances).

``swift_topology_file`` should contain mapping between swift nodes and
racks in the following format:

.. sourcecode:: cfg

    node1 /rack1
    node2 /rack2
    node3 /rack2

Note that the swift node must be exactly the same as configures in object.builder
swift ring. Also make sure that VMs with the task tracker service have direct access
to swift nodes.

Hadoop versions after 1.2.0 support four-layer topology
(https://issues.apache.org/jira/browse/HADOOP-8468). To enable this feature
set ``enable_hypervisor_awareness`` option to ``True`` in Sahara configuration
file. In this case Sahara will add the compute node ID as a second level of
topology for Virtual Machines.

Security group management
-------------------------

Sahara allows you to control which security groups will be used for created
instances. This can be done by providing the ``security_groups`` parameter for
the Node Group or Node Group Template. By default an empty list is used that
will result in using the default security group.

Sahara may also create a security group for instances in the node group
automatically. This security group will only have open ports which are
required by instance processes or the Sahara engine. This option is useful
for development and secured from outside environments, but for production
environments it is recommended to control the security group policy manually.

Heat Integration
----------------

Sahara may use
`OpenStack Orchestration engine <https://wiki.openstack.org/wiki/Heat>`_
(aka Heat) to provision nodes for Hadoop cluster.
To make Sahara work with Heat the following steps are required:

* Your OpenStack installation must have 'orchestration' service up and running
* Sahara must contain the following configuration parameter in *sahara.conf*:

.. sourcecode:: cfg

    # An engine which will be used to provision infrastructure for Hadoop cluster. (string value)
    infrastructure_engine=heat


There is a feature parity between direct and heat infrastructure engines. It is
recommended to use the heat engine since the direct engine will be deprecated at some
point.

Multi region deployment
-----------------------
Sahara supports multi region deployment. In this case, each instance of Sahara
should have the ``os_region_name=<region>`` property set in the
configuration file.

Hadoop HDFS High Availability
-----------------------------
Hadoop HDFS High Availability (HDFS HA) uses 2 Namenodes in an active/standby
architecture to ensure that HDFS will continue to work even when the active namenode fails.
The High Availability is achieved by using a set of JournalNodes and Zookeeper servers along
with ZooKeeper Failover Controllers (ZKFC) and some additional configurations and changes to
HDFS and other services that use HDFS.

Currently HDFS HA is only supported with the HDP 2.0.6 plugin. The feature is enabled through
a cluster_configs parameter in the cluster's JSON:

.. sourcecode:: cfg
        "cluster_configs": {
                "HDFSHA": {
                        "hdfs.nnha": true
                }
        }

Plugin Capabilities
-------------------
The below tables provides a plugin capability matrix:

+--------------------------+---------+----------+----------+-------+
|                          | Plugin                                |
|                          +---------+----------+----------+-------+
| Feature                  | Vanilla | HDP      | Cloudera | Spark |
+==========================+=========+==========+==========+=======+
| Nova and Neutron network | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+
| Cluster Scaling          | x       | Scale Up | x        | x     |
+--------------------------+---------+----------+----------+-------+
| Swift Integration        | x       | x        | x        | N/A   |
+--------------------------+---------+----------+----------+-------+
| Cinder Support           | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+
| Data Locality            | x       | x        | N/A      | x     |
+--------------------------+---------+----------+----------+-------+
| EDP                      | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+

Running Sahara in Distributed Mode
----------------------------------

.. warning::
    Currently distributed mode for Sahara is in alpha state. We do not
    recommend using it in a production environment.

The :doc:`installation.guide` suggests to launch
Sahara as a single 'sahara-all' process. It is also possible to run Sahara
in distributed mode with 'sahara-api' and 'sahara-engine' processes running
on several machines simultaneously.

Sahara-api works as a front-end and serves users' requests. It
offloads 'heavy' tasks to the sahara-engine via RPC mechanism. While the
sahara-engine could be loaded, sahara-api by design stays free
and hence may quickly respond on user queries.

If Sahara runs on several machines, the API requests could be
balanced between several sahara-api instances using a load balancer.
It is not required to balance load between different sahara-engine
instances, as that will be automatically done via a message queue.

If a single machine goes down, others will continue serving
users' requests. Hence a better scalability is achieved and some
fault tolerance as well. Note that the proposed solution is not
a true High Availability. While failure of a single machine does not
affect work of other machines, all of the operations running on
the failed machine will stop. For example, if a cluster
scaling is interrupted, the cluster will be stuck in a half-scaled state.
The cluster will probably continue working, but it will be impossible
to scale it further or run jobs on it via EDP.

To run Sahara in distributed mode pick several machines on which
you want to run Sahara services and follow these steps:

 * On each machine install and configure Sahara using the
   `installation guide <../installation.guide.html>`_
   except:

    * Do not run 'sahara-db-manage' or launch Sahara with 'sahara-all'
    * Make sure sahara.conf provides database connection string to a
      single database on all machines.

 * Run 'sahara-db-manage' as described in the installation guide,
   but only on a single (arbitrarily picked) machine.

 * sahara-api and sahara-engine processes use oslo.messaging to
   communicate with each other. You need to configure it properly on
   each node (see below).

 * run sahara-api and sahara-engine on the desired nodes. On a node
   you can run both sahara-api and sahara-engine or you can run them on
   separate nodes. It does not matter as long as they are configured
   to use the same message broker and database.

To configure oslo.messaging, first you need to pick the driver you are
going to use. Right now three drivers are provided: Rabbit MQ, Qpid or Zmq.
To use Rabbit MQ or Qpid driver, you will have to setup messaging broker.
The picked driver must be supplied in ``sahara.conf`` in
``[DEFAULT]/rpc_backend`` parameter. Use one the following values:
``rabbit``, ``qpid`` or ``zmq``. Next you have to supply
driver-specific options.

Unfortunately, right now there is no documentation with a description of
drivers' configuration. The options are available only in source code.

 * For Rabbit MQ see

   * rabbit_opts variable in `impl_rabbit.py <https://git.openstack.org/cgit/openstack/oslo.messaging/tree/oslo/messaging/_drivers/impl_rabbit.py?id=1.4.0#n38>`_
   * amqp_opts variable in `amqp.py <https://git.openstack.org/cgit/openstack/oslo.messaging/tree/oslo/messaging/_drivers/amqp.py?id=1.4.0#n37>`_

 * For Qpid see

   * qpid_opts variable in `impl_qpid.py <https://git.openstack.org/cgit/openstack/oslo.messaging/tree/oslo/messaging/_drivers/impl_qpid.py?id=1.4.0#n40>`_
   * amqp_opts variable in `amqp.py <https://git.openstack.org/cgit/openstack/oslo.messaging/tree/oslo/messaging/_drivers/amqp.py?id=1.4.0#n37>`_

 * For Zmq see

   * zmq_opts variable in `impl_zmq.py <https://git.openstack.org/cgit/openstack/oslo.messaging/tree/oslo/messaging/_drivers/impl_zmq.py?id=1.4.0#n49>`_
   * matchmaker_opts variable in `matchmaker.py <https://git.openstack.org/cgit/openstack/oslo.messaging/tree/oslo/messaging/_drivers/matchmaker.py?id=1.4.0#n27>`_
   * matchmaker_redis_opts variable in `matchmaker_redis.py <https://git.openstack.org/cgit/openstack/oslo.messaging/tree/oslo/messaging/_drivers/matchmaker_redis.py?id=1.4.0#n26>`_
   * matchmaker_opts variable in `matchmaker_ring.py <https://git.openstack.org/cgit/openstack/oslo.messaging/tree/oslo/messaging/_drivers/matchmaker_ring.py?id=1.4.0#n27>`_

You can find the same options defined in ``sahara.conf.sample``. You can use
it to find section names for each option (matchmaker options are
defined not in ``[DEFAULT]``)
