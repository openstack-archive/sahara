Features Overview
=================

This page highlights some of the most prominent features available in
sahara. The guidance provided here is primarily focused on the
runtime aspects of sahara. For discussions about configuring the sahara
server processes please see the :doc:`../admin/configuration-guide` and
:doc:`../admin/advanced-configuration-guide`.

Anti-affinity
-------------

One of the problems with running data processing applications on OpenStack
is the inability to control where an instance is actually running. It is
not always possible to ensure that two new virtual machines are started on
different physical machines. As a result, any replication within the cluster
is not reliable because all replicas may be co-located on one physical
machine. To remedy this, sahara provides the anti-affinity feature to
explicitly command all instances of the specified processes to spawn on
different Compute nodes. This is especially useful for Hadoop data node
processes to increase HDFS replica reliability.

Starting with the Juno release, sahara can create server groups with the
``anti-affinity`` policy to enable this feature. Sahara creates one server
group per cluster and assigns all instances with affected processes to
this server group. Refer to the :nova-doc:`Nova Anti-Affinity documentation
<admin/configuration/schedulers.html#servergroupantiaffinityfilter>`
on how server group affinity filters work.

This feature is supported by all plugins out of the box, and can be enabled
during the cluster template creation.

Block Storage support
---------------------

OpenStack Block Storage (cinder) can be used as an alternative for
ephemeral drives on instances. Using Block Storage volumes increases the
reliability of data which is important for HDFS services.

A user can set how many volumes will be attached to each instance in a
node group and the size of each volume. All volumes are attached during
cluster creation and scaling operations.

If volumes are used for the HDFS storage it's important to make sure that
the linear read-write operations as well as IOpS level are high enough to
handle the workload. Volumes placed on the same compute host provide a higher
level of performance.

In some cases cinder volumes can be backed by a distributed storage like Ceph.
In this type of installation it's important to make sure that the network
latency and speed do not become a blocker for HDFS. Distributed storage
solutions usually provide their own replication mechanism. HDFS replication
should be disabled so that it does not generate redundant traffic across the
cloud.

Cluster scaling
---------------

Cluster scaling allows users to change the number of running instances
in a cluster without needing to recreate the cluster. Users may
increase or decrease the number of instances in node groups or add
new node groups to existing clusters. If a cluster fails to scale
properly, all changes will be rolled back.

Data locality
-------------

For optimal performance, it is best for data processing applications
to work on data local to the same rack, OpenStack Compute node, or
virtual machine. Hadoop supports a data locality feature and can schedule
jobs to task tracker nodes that are local for the input stream. In this
manner the task tracker nodes can communicate directly with the local
data nodes.

Sahara supports topology configuration for HDFS and Object Storage
data sources. For more information on configuring this option please
see the :ref:`data_locality_configuration` documentation.

Volume-to-instance locality
---------------------------

Having an instance and an attached volume on the same physical host can
be very helpful in order to achieve high-performance disk I/O operations.
To achieve this, sahara provides access to the Block Storage
volume instance locality functionality.

For more information on using volume instance locality with sahara,
please see the :ref:`volume_instance_locality_configuration`
documentation.

Distributed Mode
----------------

The :doc:`../install/installation-guide` suggests launching sahara in
distributed mode with ``sahara-api`` and ``sahara-engine`` processes
potentially running on several machines simultaneously.
Running in distributed mode allows sahara to
offload intensive tasks to the engine processes while keeping the API
process free to handle requests.

For an expanded discussion of configuring sahara to run in distributed
mode please see the :ref:`distributed-mode-configuration` documentation.

Hadoop HDFS and YARN High Availability
--------------------------------------

Currently HDFS and YARN HA are supported with the HDP 2.4 plugin and CDH 5.7
plugins.

Hadoop HDFS and YARN High Availability provide an architecture to ensure
that HDFS or YARN will continue to work in the result of an active namenode or
resourcemanager failure. They use 2 namenodes and 2 resourcemanagers in an
active/passive state to provide this availability.

In the HDP 2.4 plugin, the feature can be enabled through dashboard in the
Cluster Template creation form. High availability is achieved by using a set
of journalnodes, Zookeeper servers, and ZooKeeper Failover Controllers (ZKFC),
as well as additional configuration changes to HDFS and other services that
use HDFS.

In the CDH 5.7 plugin, HA for HDFS and YARN is enabled through adding several
HDFS_JOURNALNODE roles in the node group templates of cluster template.
The HDFS HA is enabled when HDFS_JOURNALNODE roles are added and the roles
setup meets below requirements:

* HDFS_JOURNALNODE number is odd, and at least 3.
* Zookeeper is enabled.
* NameNode and SecondaryNameNode are on different physical hosts by setting
  anti-affinity.
* Cluster has both ResourceManager and StandByResourceManager.

In this case, the original SecondaryNameNode node will be used as the
Standby NameNode.


Networking support
------------------

Sahara supports neutron implementations of OpenStack Networking.

Object Storage support
----------------------

Sahara can use OpenStack Object Storage (swift) to store job binaries and data
sources utilized by its job executions and clusters. In order to
leverage this support within Hadoop, including using Object Storage
for data sources for EDP, Hadoop requires the application of
a patch. For additional information about enabling this support,
including patching Hadoop and configuring sahara, please refer to
the :doc:`hadoop-swift` documentation.

Shared Filesystem support
-------------------------

Sahara can also use NFS shares through the OpenStack Shared Filesystem service
(manila) to store job binaries and data sources. See :doc:`edp` for more
information on this feature.

Orchestration support
---------------------

Sahara may use the
`OpenStack Orchestration engine <https://wiki.openstack.org/wiki/Heat>`_
(heat) to provision nodes for clusters. For more information about
enabling Orchestration usage in sahara please see
:ref:`orchestration-configuration`.

DNS support
-----------

Sahara can resolve hostnames of cluster instances by using DNS. For this Sahara
uses designate. For additional details see
:doc:`../admin/advanced-configuration-guide`.

Kerberos support
----------------

You can protect your HDP or CDH cluster using MIT Kerberos security. To get
more details about this, please, see documentation for the appropriate plugin.

Plugin Capabilities
-------------------

The following table provides a plugin capability matrix:

+--------------------------+---------+----------+----------+-------+
| Feature/Plugin           | Vanilla |   HDP    | Cloudera | Spark |
+==========================+=========+==========+==========+=======+
| Neutron network          | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+
| Cluster Scaling          | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+
| Swift Integration        | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+
| Cinder Support           | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+
| Data Locality            | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+
| DNS                      | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+
| Kerberos                 | \-      | x        | x        | \-    |
+--------------------------+---------+----------+----------+-------+
| HDFS HA                  | \-      | x        | x        | \-    |
+--------------------------+---------+----------+----------+-------+
| EDP                      | x       | x        | x        | x     |
+--------------------------+---------+----------+----------+-------+

Security group management
-------------------------

Security groups are sets of IP filter rules that are applied to an instance's
networking. They are project specified, and project members can edit the
default rules for their group and add new rules sets. All projects have a
"default" security group, which is applied to instances that have no other
security group defined. Unless changed, this security group denies all incoming
traffic.

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

Shared and protected resources support
--------------------------------------

Sahara allows you to create resources that can be shared across projects and
protected from modifications.

To provide this feature all sahara objects that can be accessed through
REST API have ``is_public`` and ``is_protected`` boolean fields. They can be
initially created with enabled ``is_public`` and ``is_protected``
parameters or these parameters can be updated after creation. Both fields are
set to ``False`` by default.

If some object has its ``is_public`` field set to ``True``, it means that it's
visible not only from the project in which it was created, but from any other
projects too.

If some object has its ``is_protected`` field set to ``True``, it means that it
can not be modified (updated, scaled, canceled or deleted) unless this field
is set to ``False``.

Public objects created in one project can be used from other projects (for
example, a cluster can be created from a public cluster template which is
created in another project), but modification operations are possible only from
the project in which object was created.

Data source placeholders support
--------------------------------

Sahara supports special strings that can be used in data source URLs. These
strings will be replaced with appropriate values during job execution which
allows the use of the same data source as an output multiple times.

There are 2 types of string currently supported:

* ``%JOB_EXEC_ID%`` - this string will be replaced with the job execution ID.
* ``%RANDSTR(len)%`` - this string will be replaced with random string of
  lowercase letters of length ``len``. ``len`` must be less than 1024.

After placeholders are replaced, the real URLs are stored in the
``data_source_urls`` field of the job execution object. This is used later to
find objects created by a particular job run.

Keypair replacement
-------------------

A cluster allows users to create a new keypair to access to the running cluster
when the cluster's keypair is deleted. But the name of new keypair should be
same as the deleted one, and the new keypair will be available for cluster
scaling.
