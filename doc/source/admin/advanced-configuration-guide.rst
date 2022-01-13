Sahara Advanced Configuration Guide
===================================

This guide addresses specific aspects of Sahara configuration that pertain to
advanced usage. It is divided into sections about various features that can be
utilized, and their related configurations.

.. _custom_network_topologies:

Custom network topologies
-------------------------

Sahara accesses instances at several stages of cluster spawning through
SSH and HTTP. Floating IPs and network namespaces will be automatically
used for access when present. When floating IPs are not assigned to
instances and namespaces are not being used, sahara will need an
alternative method to reach them.

The ``proxy_command`` parameter of the configuration file can be used to
give sahara a command to access instances. This command is run on the
sahara host and must open a netcat socket to the instance destination
port. The ``{host}`` and ``{port}`` keywords should be used to describe the
destination, they will be substituted at runtime.  Other keywords that
can be used are: ``{tenant_id}``, ``{network_id}`` and ``{router_id}``.

Additionally, if ``proxy_command_use_internal_ip`` is set to ``True``,
then the internal IP will be substituted for ``{host}`` in the command.
Otherwise (if ``False``, by default) the management IP will be used: this
corresponds to floating IP if present in the relevant node group, else the
internal IP. The option is ignored if ``proxy_command`` is not also set.

For example, the following parameter in the sahara configuration file
would be used if instances are accessed through a relay machine:

.. code-block::

    [DEFAULT]
    proxy_command='ssh relay-machine-{tenant_id} nc {host} {port}'

Whereas the following shows an example of accessing instances though
a custom network namespace:

.. code-block::

    [DEFAULT]
    proxy_command='ip netns exec ns_for_{network_id} nc {host} {port}'

.. _dns_hostname_resolution:

DNS Hostname Resolution
-----------------------

Sahara can resolve hostnames of cluster instances by using DNS. For this Sahara
uses Designate. With this feature, for each instance of the cluster Sahara will
create two ``A`` records (for internal and external ips) under one hostname
and one ``PTR`` record. Also all links in the Sahara dashboard will be
displayed as hostnames instead of just ip addresses.

You should configure DNS server with Designate. Designate service should be
properly installed and registered in Keystone catalog. The detailed
instructions about Designate configuration can be found here:
:designate-doc:`Designate manual installation <install/index.html>`
and here: :neutron-doc:`Configuring OpenStack Networking with Designate
<admin/config-dns-int.html#configuring-openstack-networking-for-integration-with-an-external-dns-service>`.
Also if you use devstack you can just enable the
:designate-doc:`Designate devstack plugin <contributor/devstack.html>`.

When Designate is configured you should create domain(s) for hostname
resolution. This can be done by using the Designate dashboard or by CLI. Also
you have to create ``in-addr.arpa.`` domain for reverse hostname resolution
because some plugins (e.g. ``HDP``) determine hostname by ip.

Sahara also should be properly configured. In ``sahara.conf`` you must specify
two config properties:

.. code-block::

    [DEFAULT]
    # Use Designate for internal and external hostnames resolution:
    use_designate=true
    # IP addresses of Designate nameservers:
    nameservers=1.1.1.1,2.2.2.2

An OpenStack operator should properly configure the network. It must enable
DHCP and specify DNS server ip addresses (e.g. 1.1.1.1 and 2.2.2.2) in
``DNS Name Servers`` field in the ``Subnet Details``. If the subnet already
exists and changing it or creating new one is impossible then Sahara will
manually change ``/etc/resolv.conf`` file on every instance of the cluster (if
``nameservers`` list has been specified in ``sahara.conf``). In this case,
though, Sahara cannot guarantee that these changes will not be overwritten by
DHCP or other services of the existing network. Sahara has a health check for
track this situation (and if it occurs the health status will be red).

In order to resolve hostnames from your local machine you should properly
change your ``/etc/resolv.conf`` file by adding appropriate ip addresses of
DNS servers (e.g. 1.1.1.1 and 2.2.2.2). Also the VMs with DNS servers should
be available from your local machine.

.. _data_locality_configuration:

Data-locality configuration
---------------------------

Hadoop provides the data-locality feature to enable task tracker and
data nodes the capability of spawning on the same rack, Compute node,
or virtual machine. Sahara exposes this functionality to the user
through a few configuration parameters and user defined topology files.

To enable data-locality, set the ``enable_data_locality`` parameter to
``true`` in the sahara configuration file

.. code-block::

    [DEFAULT]
    enable_data_locality=true

With data locality enabled, you must now specify the topology files
for the Compute and Object Storage services. These files are
specified in the sahara configuration file as follows:

.. code-block::

    [DEFAULT]
    compute_topology_file=/etc/sahara/compute.topology
    swift_topology_file=/etc/sahara/swift.topology

The ``compute_topology_file`` should contain mappings between Compute
nodes and racks in the following format:

.. code-block::

    compute1 /rack1
    compute2 /rack2
    compute3 /rack2

Note that the Compute node names must be exactly the same as configured in
OpenStack (``host`` column in admin list for instances).

The ``swift_topology_file`` should contain mappings between Object Storage
nodes and racks in the following format:

.. code-block::

    node1 /rack1
    node2 /rack2
    node3 /rack2

Note that the Object Storage node names must be exactly the same as
configured in the object ring. Also, you should ensure that instances
with the task tracker process have direct access to the Object Storage
nodes.

Hadoop versions after 1.2.0 support four-layer topology (for more detail
please see `HADOOP-8468 JIRA issue`_). To enable this feature set the
``enable_hypervisor_awareness`` parameter to ``true`` in the configuration
file. In this case sahara will add the Compute node ID as a second level of
topology for virtual machines.

.. _HADOOP-8468 JIRA issue: https://issues.apache.org/jira/browse/HADOOP-8468

.. _distributed-mode-configuration:

Distributed mode configuration
------------------------------

Sahara can be configured to run in a distributed mode that creates a
separation between the API and engine processes. This allows the API
process to remain relatively free to handle requests while offloading
intensive tasks to the engine processes.

The ``sahara-api`` application works as a front-end and serves user
requests. It offloads 'heavy' tasks to the ``sahara-engine`` process
via RPC mechanisms. While the ``sahara-engine`` process could be loaded
with tasks, ``sahara-api`` stays free and hence may quickly respond to
user queries.

If sahara runs on several hosts, the API requests could be
balanced between several ``sahara-api`` hosts using a load balancer.
It is not required to balance load between different ``sahara-engine``
hosts as this will be automatically done via the message broker.

If a single host becomes unavailable, other hosts will continue
serving user requests. Hence, a better scalability is achieved and some
fault tolerance as well. Note that distributed mode is not a true
high availability. While the failure of a single host does not
affect the work of the others, all of the operations running on
the failed host will stop. For example, if a cluster scaling is
interrupted, the cluster will be stuck in a half-scaled state. The
cluster might continue working, but it will be impossible to scale it
further or run jobs on it via EDP.

To run sahara in distributed mode pick several hosts on which
you want to run sahara services and follow these steps:

* On each host install and configure sahara using the
  `installation guide <../install/installation-guide.html>`_
  except:

  * Do not run ``sahara-db-manage`` or launch sahara with ``sahara-all``
  * Ensure that each configuration file provides a database connection
    string to a single database for all hosts.

* Run ``sahara-db-manage`` as described in the installation guide,
  but only on a single (arbitrarily picked) host.

* The ``sahara-api`` and ``sahara-engine`` processes use oslo.messaging to
  communicate with each other. You will need to configure it properly on
  each host (see below).

* Run ``sahara-api`` and ``sahara-engine`` on the desired hosts. You may
  run both processes on the same or separate hosts as long as they are
  configured to use the same message broker and database.

To configure ``oslo.messaging``, first you need to choose a message
broker driver. The recommended driver is ``RabbitMQ``. For the ``RabbitMQ``
drivers please see the :ref:`notification-configuration` documentation
for an explanation of common configuration options; the entire list of
configuration options is found in the
:oslo.messaging-doc:`oslo_messaging_rabbit documentation
<configuration/opts.html#oslo-messaging-rabbit>`.

These options will also be present in the generated sample configuration
file. For instructions on creating the configuration file please see the
:doc:`configuration-guide`.

.. _distributed-periodic-tasks:

Distributed periodic tasks configuration
----------------------------------------

If sahara is configured to run in distributed mode (see
:ref:`distributed-mode-configuration`), periodic tasks can also be launched in
distributed mode. In this case tasks will be split across all ``sahara-engine``
processes. This will reduce overall load.

Distributed periodic tasks are based on Hash Ring implementation and the Tooz
library that provides group membership support for a set of backends. In order
to use periodic tasks distribution, the following steps are required:

* One of the :tooz-doc:`supported backends <user/compatibility.html#driver-support>`
  should be configured and started.
* Backend URL should be set in the sahara configuration file with the
  ``periodic_coordinator_backend_url`` parameter. For example, if the
  ZooKeeper backend is being used:

  .. code-block::

      [DEFAULT]
      periodic_coordinator_backend_url=kazoo://IP:PORT

* Tooz extras should be installed. When using Zookeeper as coordination
  backend, ``kazoo`` library should be installed. It can be done with pip:

  .. code-block::

      pip install tooz[zookeeper]

* Periodic tasks can be performed in parallel. Number of threads to run
  periodic tasks on a single engine can be set with
  ``periodic_workers_number`` parameter (only 1 thread will be launched by
  default). Example:

  .. code-block::

      [DEFAULT]
      periodic_workers_number=2

* ``coordinator_heartbeat_interval`` can be set to change the interval between
  heartbeat execution (1 second by default). Heartbeats are needed to make
  sure that connection to the coordination backend is active. Example:

  .. code-block::

      [DEFAULT]
      coordinator_heartbeat_interval=2

* ``hash_ring_replicas_count`` can be set to change the number of replicas for
  each engine on a Hash Ring. Each replica is a point on a Hash Ring that
  belongs to a particular engine. A larger number of replicas leads to better
  task distribution across the set of engines. (40 by default). Example:

  .. code-block::

      [DEFAULT]
       hash_ring_replicas_count=100

.. _external_key_manager_usage:

External key manager usage
--------------------------

Sahara generates and stores several passwords during the course of operation.
To harden sahara's usage of passwords it can be instructed to use an
external key manager for storage and retrieval of these secrets. To enable
this feature there must first be an OpenStack Key Manager service deployed
within the stack.

With a Key Manager service deployed on the stack, sahara must be configured
to enable the external storage of secrets. Sahara uses the
:castellan-doc:`castellan <>` library
to interface with the OpenStack Key Manager service. This library provides
configurable access to a key manager. To configure sahara to use barbican as
the key manager, edit the sahara configuration file as follows:

.. code-block::

    [DEFAULT]
    use_barbican_key_manager=true

Enabling the ``use_barbican_key_manager`` option will configure castellan
to use barbican as its key management implementation. By default it will
attempt to find barbican in the Identity service's service catalog.

For added control of the barbican server location, optional configuration
values may be added to specify the URL for the barbican API server.

.. code-block::

    [castellan]
    barbican_api_endpoint=http://{barbican controller IP:PORT}/
    barbican_api_version=v1

The specific values for the barbican endpoint will be dictated by the
IP address of the controller for your installation.

With all of these values configured and the Key Manager service deployed,
sahara will begin storing its secrets in the external manager.

Indirect instance access through proxy nodes
--------------------------------------------

.. warning::
    The indirect VMs access feature is in alpha state. We do not
    recommend using it in a production environment.

Sahara needs to access instances through SSH during cluster setup. This
access can be obtained a number of different ways (see
:ref:`floating_ip_management`,:ref:`custom_network_topologies`).Sometimes
it is impossible to provide access to all nodes (because of limited
numbers of floating IPs or security policies). In these cases access can
be gained using other nodes of the cluster as proxy gateways. To enable
this set ``is_proxy_gateway=true`` for the node group you want to use as
proxy. Sahara will communicate with all other cluster instances through
the instances of this node group.

Note, if ``use_floating_ips=true`` and the cluster contains a node group with
``is_proxy_gateway=true``, the requirement to have ``floating_ip_pool``
specified is applied only to the proxy node group. Other instances will be
accessed through proxy instances using the standard private network.

Note, the Cloudera Hadoop plugin doesn't support access to Cloudera manager
through a proxy node. This means that for CDH clusters only nodes with
the Cloudera manager can be designated as proxy gateway nodes.

Multi region deployment
-----------------------

Sahara supports multi region deployment. To enable this option each
instance of sahara should have the ``os_region_name=<region>``
parameter set in the configuration file. The following example demonstrates
configuring sahara to use the ``RegionOne`` region:

.. code-block::

    [DEFAULT]
    os_region_name=RegionOne

.. _non-root-users:

Non-root users
--------------

In cases where a proxy command is being used to access cluster instances
(for example, when using namespaces or when specifying a custom proxy
command), rootwrap functionality is provided to allow users other than
``root`` access to the needed operating system facilities. To use rootwrap
the following configuration parameter is required to be set:

.. code-block::

    [DEFAULT]
    use_rootwrap=true

Assuming you elect to leverage the default rootwrap command
(``sahara-rootwrap``), you will need to perform the following additional setup
steps:

* Copy the provided sudoers configuration file from the local project file
  ``etc/sudoers.d/sahara-rootwrap`` to the system specific location, usually
  ``/etc/sudoers.d``. This file is setup to allow a user named ``sahara``
  access to the rootwrap script. It contains the following:

.. code-block::

    sahara ALL = (root) NOPASSWD: /usr/bin/sahara-rootwrap /etc/sahara/rootwrap.conf *

When using devstack to deploy sahara, please pay attention that you need to
change user in script from ``sahara`` to ``stack``.

* Copy the provided rootwrap configuration file from the local project file
  ``etc/sahara/rootwrap.conf`` to the system specific location, usually
  ``/etc/sahara``. This file contains the default configuration for rootwrap.

* Copy the provided rootwrap filters file from the local project file
  ``etc/sahara/rootwrap.d/sahara.filters`` to the location specified in the
  rootwrap configuration file, usually ``/etc/sahara/rootwrap.d``. This file
  contains the filters that will allow the ``sahara`` user to access the
  ``ip netns exec``, ``nc``, and ``kill`` commands through the rootwrap
  (depending on ``proxy_command`` you may need to set additional filters).
  It should look similar to the followings:

.. code-block::

    [Filters]
    ip: IpNetnsExecFilter, ip, root
    nc: CommandFilter, nc, root
    kill: CommandFilter, kill, root

If you wish to use a rootwrap command other than ``sahara-rootwrap`` you can
set the following parameter in your sahara configuration file:

.. code-block::

    [DEFAULT]
    rootwrap_command='sudo sahara-rootwrap /etc/sahara/rootwrap.conf'

For more information on rootwrap please refer to the
`official Rootwrap documentation <https://wiki.openstack.org/wiki/Rootwrap>`_

Object Storage access using proxy users
---------------------------------------

To improve security for clusters accessing files in Object Storage,
sahara can be configured to use proxy users and delegated trusts for
access. This behavior has been implemented to reduce the need for
storing and distributing user credentials.

The use of proxy users involves creating an Identity domain that will be
designated as the home for these users. Proxy users will be
created on demand by sahara and will only exist during a job execution
which requires Object Storage access. The domain created for the
proxy users must be backed by a driver that allows sahara's admin user to
create new user accounts. This new domain should contain no roles, to limit
the potential access of a proxy user.

Once the domain has been created, sahara must be configured to use it by
adding the domain name and any potential delegated roles that must be used
for Object Storage access to the sahara configuration file. With the
domain enabled in sahara, users will no longer be required to enter
credentials for their data sources and job binaries referenced in
Object Storage.

Detailed instructions
^^^^^^^^^^^^^^^^^^^^^

First a domain must be created in the Identity service to hold proxy
users created by sahara. This domain must have an identity backend driver
that allows for sahara to create new users. The default SQL engine is
sufficient but if your keystone identity is backed by LDAP or similar
then domain specific configurations should be used to ensure sahara's
access. Please see the :keystone-doc:`Keystone documentation
<configuration.html#domain-specific-drivers>` for more information.

With the domain created, sahara's configuration file should be updated to
include the new domain name and any potential roles that will be needed. For
this example let's assume that the name of the proxy domain is
``sahara_proxy`` and the roles needed by proxy users will be ``member`` and
``SwiftUser``.

.. code-block::

    [DEFAULT]
    use_domain_for_proxy_users=true
    proxy_user_domain_name=sahara_proxy
    proxy_user_role_names=member,SwiftUser

A note on the use of roles. In the context of the proxy user, any roles
specified here are roles intended to be delegated to the proxy user from the
user with access to Object Storage. More specifically, any roles that
are required for Object Storage access by the project owning the object
store must be delegated to the proxy user for authentication to be
successful.

Finally, the stack administrator must ensure that images registered with
sahara have the latest version of the Hadoop swift filesystem plugin
installed. The sources for this plugin can be found in the
`sahara extra repository`_. For more information on images or swift
integration see the sahara documentation sections
:ref:`building-guest-images-label` and :ref:`swift-integration-label`.

.. _Sahara extra repository: https://opendev.org/openstack/sahara-extra

.. _volume_instance_locality_configuration:

Volume instance locality configuration
--------------------------------------

The Block Storage service provides the ability to define volume instance
locality to ensure that instance volumes are created on the same host
as the hypervisor. The ``InstanceLocalityFilter`` provides the mechanism
for the selection of a storage provider located on the same physical
host as an instance.

To enable this functionality for instances of a specific node group, the
``volume_local_to_instance`` field in the node group template should be
set to ``true`` and some extra configurations are needed:

* The cinder-volume service should be launched on every physical host and at
  least one physical host should run both cinder-scheduler and
  cinder-volume services.
* ``InstanceLocalityFilter`` should be added to the list of default filters
  (``scheduler_default_filters`` in cinder) for the Block Storage
  configuration.
* The Extended Server Attributes extension needs to be active in the Compute
  service (this is true by default in nova), so that the
  ``OS-EXT-SRV-ATTR:host`` property is returned when requesting instance
  info.
* The user making the call needs to have sufficient rights for the property to
  be returned by the Compute service.
  This can be done by:

  * by changing nova's ``policy.yaml`` to allow the user access to the
    ``extended_server_attributes`` option.
  * by designating an account with privileged rights in the cinder
    configuration:

    .. code-block::

        os_privileged_user_name =
        os_privileged_user_password =
        os_privileged_user_tenant =

It should be noted that in a situation when the host has no space for volume
creation, the created volume will have an ``Error`` state and can not be used.

Autoconfiguration for templates
-------------------------------

:doc:`configs-recommendations`


NTP service configuration
-------------------------

By default sahara will enable the NTP service on all cluster instances if the
NTP package is included in the image (the sahara disk image builder will
include NTP in all images it generates). The default NTP server will be
``pool.ntp.org``; this can be overridden using the ``default_ntp_server``
setting in the ``DEFAULT`` section of the sahara configuration file.

If you are creating cluster templates using the sahara UI and would like to
specify a different NTP server for a particular cluster template, use the ``URL
of NTP server`` setting in the ``General Parameters`` section when you create
the template. If you would like to disable NTP for a particular cluster
template, deselect the ``Enable NTP service`` checkbox in the ``General
Parameters`` section when you create the template.

If you are creating clusters using the sahara CLI, you can specify another NTP
server or disable NTP service using the examples below.

If you want to enable configuring the NTP service, you should specify the
following configs for the cluster:

.. code-block::

  {
      "cluster_configs": {
          "general": {
              "URL of NTP server": "your_server.net"
          }
      }
  }

If you want to disable configuring NTP service, you should specify following
configs for the cluster:

.. code-block::

  {
      "cluster_configs": {
          "general": {
              "Enable NTP service": false
          }
      }
  }

CORS (Cross Origin Resource Sharing) Configuration
--------------------------------------------------

Sahara provides direct API access to user-agents (browsers) via the HTTP
CORS protocol. Detailed documentation, as well as troubleshooting examples,
may be found in the :oslo.middleware-doc:`documentation of the oslo.db
cross-project features <admin/cross-project-cors.html>`.

To get started quickly, use the example configuration block below, replacing
the :code:`allowed origin` field with the host(s) from which your API expects
access.

.. code-block::

    [cors]
    allowed_origin=https://we.example.com:443
    max_age=3600
    allow_credentials=true

    [cors.additional_domain_1]
    allowed_origin=https://additional_domain_1.example.com:443

    [cors.additional_domain_2]
    allowed_origin=https://additional_domain_2.example.com:443

For more information on Cross Origin Resource Sharing, please review the `W3C
CORS specification`_.

.. _W3C CORS specification: http://www.w3.org/TR/cors/

Cleanup time for incomplete clusters
------------------------------------

Sahara provides maximal time (in hours) for clusters allowed to be in states
other than "Active", "Deleting" or "Error". If a cluster is not in "Active",
"Deleting" or "Error" state and last update of it was longer than
``cleanup_time_for_incomplete_clusters`` hours ago then it will be deleted
automatically. You can enable this feature by adding appropriate config
property in the ``DEFAULT`` section (by default it set up to ``0`` value which
means that automatic clean up is disabled). For example, if you want cluster to
be deleted after 3 hours if it didn't leave "Starting" state then you should
specify:

.. code-block::

    [DEFAULT]
    cleanup_time_for_incomplete_clusters = 3

Security Group Rules Configuration
----------------------------------

When auto_security_group is used, the amount of created security group rules
may be bigger than the default values configured in ``neutron.conf``. Then the
default limit should be raised up to some bigger value which is proportional to
the number of cluster node groups. You can change it in ``neutron.conf`` file:

.. code-block::

    [quotas]
    quota_security_group = 1000
    quota_security_group_rule = 10000

Or you can execute openstack CLI command:

.. code-block::

    openstack quota set --secgroups 1000 --secgroup-rules 10000 $PROJECT_ID
