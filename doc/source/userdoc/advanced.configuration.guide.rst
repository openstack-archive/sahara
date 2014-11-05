Sahara Advanced Configuration Guide
===================================

This guide addresses specific aspects of Sahara configuration that pertain to
advanced usage. It is divided into sections about various features that can be
utilized, and their related configurations.

Domain usage for Swift proxy users
----------------------------------

To improve security for Sahara clusters accessing Swift objects, Sahara can be
configured to use proxy users and delegated trusts for access. This behavior
has been implemented to reduce the need for storing and distributing user
credentials.

The use of proxy users involves creating a domain in Keystone that will be
designated as the home for any proxy users created. These created users will
only exist for as long as a job execution runs. The domain created for the
proxy users must have an identity backend that allows Sahara's admin user to
create new user accounts. This new domain should contain no roles, to limit
the potential access of a proxy user.

Once the domain has been created Sahara must be configured to use it by adding
the domain name and any potential roles that must be used for Swift access in
the sahara.conf file. With the domain enabled in Sahara, users will no longer
be required to enter credentials with their Swift-backed Data Sources and Job
Binaries.

Detailed instructions
^^^^^^^^^^^^^^^^^^^^^

First a domain must be created in Keystone to hold proxy users created by
Sahara. This domain must have an identity backend that allows for Sahara to
create new users. The default SQL engine is sufficient but if your Keystone
identity is backed by LDAP or similar then domain specific configurations
should be used to ensure Sahara's access. See the `Keystone documentation`_
for more information.

.. _Keystone documentation: http://docs.openstack.org/developer/keystone/configuration.html#domain-specific-drivers

With the domain created Sahara's configuration file should be updated to
include the new domain name and any potential roles that will be needed. For
this example let's assume that the name of the proxy domain is
``sahara_proxy`` and the roles needed by proxy users will be ``Member`` and
``SwiftUser``.

.. sourcecode:: cfg

    [DEFAULT]
    use_domain_for_proxy_users=True
    proxy_user_domain_name=sahara_proxy
    proxy_user_role_names=Member,SwiftUser

..

A note on the use of roles. In the context of the proxy user, any roles
specified here are roles intended to be delegated to the proxy user from the
user with access to the Swift object store. More specifically, any roles that
are required for Swift access by the project owning the object store must be
delegated to the proxy user for Swift authentication to be successful.

Finally, the stack administrator must ensure that images registered with
Sahara have the latest version of the Hadoop Swift filesystem plugin
installed. The sources for this plugin can be found in the
`Sahara extra repository`_. For more information on images or Swift
integration see the Sahara documentation sections
:ref:`diskimage-builder-label` and :ref:`swift-integration-label`.

.. _Sahara extra repository: http://github.com/openstack/sahara-extra

Custom network topologies
-------------------------

Sahara accesses VMs at several stages of cluster spawning, both via SSH and
HTTP. When floating IPs are not assigned to instances, Sahara needs to be able
to reach them another way.  Floating IPs and network namespaces (see
:ref:`neutron-nova-network`) are automatically used when present.

When none of these are enabled, the ``proxy_command`` property can be used to
give Sahara a command to access VMs. This command is run on the Sahara host and
must open a netcat socket to the instance destination port. ``{host}`` and
``{port}`` keywords should be used to describe the destination, they will be
translated at runtime.  Other keywords can be used: ``{tenant_id}``,
``{network_id}`` and ``{router_id}``.

For instance, the following configuration property in the Sahara configuration
file would be used if VMs are accessed through a relay machine:

.. sourcecode:: cfg

    [DEFAULT]
    proxy_command='ssh relay-machine-{tenant_id} nc {host} {port}'

Whereas the following property would be used to access VMs through a custom
network namespace:

.. sourcecode:: cfg

    [DEFAULT]
    proxy_command='ip netns exec ns_for_{network_id} nc {host} {port}'


Non-root users
--------------

In cases where a proxy command is being used to access cluster VMs (for
instance when using namespaces or when specifying a custom proxy command),
rootwrap functionality is provided to allow users other than ``root`` access to
the needed OS facilities. To use rootwrap the following configuration property
is required to be set:

.. sourcecode:: cfg

    [DEFAULT]
    use_rootwrap=True


Assuming you elect to leverage the default rootwrap command
(``sahara-rootwrap``), you will need to perform the following additional setup
steps:

* Copy the provided sudoers configuration file from the local project file
  ``etc/sudoers.d/sahara-rootwrap`` to the system specific location, usually
  ``/etc/sudoers.d``. This file is setup to allow a user named ``sahara``
  access to the rootwrap script. It contains the following:

.. sourcecode:: cfg

    sahara ALL = (root) NOPASSWD: /usr/bin/sahara-rootwrap /etc/sahara/rootwrap.conf *


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

.. sourcecode:: cfg

    [Filters]
    ip: IpNetnsExecFilter, ip, root
    nc: CommandFilter, nc, root
    kill: CommandFilter, kill, root

If you wish to use a rootwrap command other than ``sahara-rootwrap`` you can
set the following configuration property in your sahara configuration file:

.. sourcecode:: cfg

    [DEFAULT]
    rootwrap_command='sudo sahara-rootwrap /etc/sahara/rootwrap.conf'

For more information on rootwrap please refer to the
`official Rootwrap documentation <https://wiki.openstack.org/wiki/Rootwrap>`_
