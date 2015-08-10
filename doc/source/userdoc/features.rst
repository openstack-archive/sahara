Features Overview
=================

This page highlights some of the most prominent features available in
sahara. The guidance provided here is primarily focused on the
runtime aspects of sahara, for discussions about configuring the sahara
server processes please see the :doc:`configuration.guide` and
:doc:`advanced.configuration.guide`.

Anti-affinity
-------------

One of the problems with running data processing applications on OpenStack
is the inability to control where an instance is actually running. It is
not always possible to ensure that two new virtual machines are started on
different physical machines. As a result, any replication within the cluster
is not reliable because all replicas may turn up on one physical machine.
To remedy this, sahara provides the anti-affinity feature to explicitly
command all instances of the specified processes to spawn on different
Compute nodes. This is especially useful for Hadoop data node processes
to increase HDFS replica reliability.

Starting with the Juno release, sahara can create server groups with the
``anti-affinity`` policy to enable this feature. Sahara creates one server
group per cluster and assigns all instances with affected processes to
this server group. Refer to the `Nova documentation`_ on how server groups
work.

This feature is supported by all plugins out of the box, and can be enabled
during the cluster template creation.

.. _Nova documentation: http://docs.openstack.org/developer/nova

Block Storage support
---------------------

OpenStack Block Storage (cinder) can be used as an alternative for
ephemeral drives on instances. Using Block Storage volumes increases the
reliability of data which is important for HDFS service.

A user can set how many volumes will be attached to each instance in a
node group, and the size of each volume.

All volumes are attached during cluster creation/scaling operations.

Cluster scaling
---------------

Cluster scaling allows users to change the number of running instances
in a cluster without needing to recreate the cluster. Users may
increase or decrease the number of instances in node groups or add
new node groups to existing clusters.

If a cluster fails to scale properly, all changes will be rolled back.

Data-locality
-------------

It is extremely important for data processing applications to perform
work locally on the same rack, OpenStack Compute node, or virtual
machine. Hadoop supports a data-locality feature and can schedule jobs
to task tracker nodes that are local for the input stream. In this
manner the task tracker nodes can communicate directly with the local
data nodes.

Sahara supports topology configuration for HDFS and Object Storage
data sources. For more information on configuring this option please
see the :ref:`data_locality_configuration` documentation.

Distributed Mode
----------------

The :doc:`installation.guide` suggests launching sahara as a single
``sahara-all`` process. It is also possible to run sahara in distributed
mode with ``sahara-api`` and ``sahara-engine`` processes running on several
machines simultaneously. Running in distributed mode allows sahara to
offload intensive tasks to the engine processes while keeping the API
process free to handle requests.

For an expanded discussion of configuring sahara to run in distributed
mode please see the :ref:`distributed-mode-configuration` documentation.

Hadoop HDFS High Availability
-----------------------------

Hadoop HDFS High Availability (HDFS HA) provides an architecture to ensure
that HDFS will continue to work in the result of an active namenode failure.
It uses 2 namenodes in an active/standby configuration to provide this
availability.

High availability is achieved by using a set of journalnodes and Zookeeper
servers along with ZooKeeper Failover Controllers (ZKFC) and additional
configuration changes to HDFS and other services that use HDFS.

Currently HDFS HA is only supported with the HDP 2.0.6 plugin. The feature
is enabled through a ``cluster_configs`` parameter in the cluster's JSON:

.. sourcecode:: cfg

        "cluster_configs": {
                "HDFSHA": {
                        "hdfs.nnha": true
                }
        }

Networking support
------------------

Sahara supports both the nova-network and neutron implementations of
OpenStack Networking. By default sahara is configured to behave as if
the nova-network implementation is available. For OpenStack installations
that are using the neutron project please see :ref:`neutron-nova-network`.

Object Storage support
----------------------

Sahara can use OpenStack Object Storage (swift) to store job binaries and data
sources utilized by its job executions and clusters. In order to
leverage this support within Hadoop, including using Object Storage
for data sources for EDP, Hadoop requires the application of
a patch. For additional information about enabling this support,
including patching Hadoop and configuring sahara, please refer to
the :doc:`hadoop-swift` documentation.

Orchestration support
---------------------

Sahara may use the
`OpenStack Orchestration engine <https://wiki.openstack.org/wiki/Heat>`_
(heat) to provision nodes for clusters. For more information about
enabling Orchestration usage in sahara please see
:ref:`orchestration-configuration`.

Plugin Capabilities
-------------------

The following table provides a plugin capability matrix:

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

Security group management
-------------------------

.. TODO (mimccune)
    This section could use an example to show how security groups are
    used.

Sahara allows you to control which security groups will be used for created
instances. This can be done by providing the ``security_groups`` parameter for
the node group or node group template. The default for this option is an
empty list, which will result in the default project security group being
used for the instances.

Sahara may also create a security group for instances in the node group
automatically. This security group will only contain open ports for required
instance processes and the sahara engine. This option is useful
for development and for when your installation is secured from outside
environments. For production environments we recommend controlling the
security group policy manually.

Volume-to-instance locality
---------------------------

Having an instance and an attached volume on the same physical host can
be very helpful in order to achieve high-performance disk I/O operations.
To achieve this, sahara provides access to the Block Storage
volume instance locality functionality.

For more information on using volume instance locality with sahara,
please see the :ref:`volume_instance_locality_configuration`
documentation.
