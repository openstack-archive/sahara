Sahara Advanced Configuration Guide
===================================

This guide addresses specific aspects of Sahara configuration that pertain to
advanced usage. It is divided into sections about various features that can be
utilized, and their related configurations.

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
for Object Storage access to the configuration file. With the
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
access. Please see the `Keystone documentation`_ for more information.

.. _Keystone documentation: http://docs.openstack.org/developer/keystone/configuration.html#domain-specific-drivers

With the domain created, sahara's configuration file should be updated to
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
user with access to Object Storage. More specifically, any roles that
are required for Object Storage access by the project owning the object
store must be delegated to the proxy user for authentication to be
successful.

Finally, the stack administrator must ensure that images registered with
sahara have the latest version of the Hadoop swift filesystem plugin
installed. The sources for this plugin can be found in the
`sahara extra repository`_. For more information on images or swift
integration see the sahara documentation sections
:ref:`diskimage-builder-label` and :ref:`swift-integration-label`.

.. _Sahara extra repository: http://github.com/openstack/sahara-extra

.. _custom_network_topologies:

Custom network topologies
-------------------------

Sahara accesses instances at several stages of cluster spawning through
SSH and HTTP. Floating IPs and network namespaces
(see :ref:`neutron-nova-network`) will be automatically used for
access when present. When floating IPs are not assigned to instances and
namespaces are not being used, sahara will need an alternative method to
reach them.

The ``proxy_command`` parameter of the configuration file can be used to
give sahara a command to access instances. This command is run on the
sahara host and must open a netcat socket to the instance destination
port. The ``{host}`` and ``{port}`` keywords should be used to describe the
destination, they will be substituted at runtime.  Other keywords that
can be used are: ``{tenant_id}``, ``{network_id}`` and ``{router_id}``.

For example, the following parameter in the sahara configuration file
would be used if instances are accessed through a relay machine:

.. sourcecode:: cfg

    [DEFAULT]
    proxy_command='ssh relay-machine-{tenant_id} nc {host} {port}'

Whereas the following shows an example of accessing instances though
a custom network namespace:

.. sourcecode:: cfg

    [DEFAULT]
    proxy_command='ip netns exec ns_for_{network_id} nc {host} {port}'


Non-root users
--------------

In cases where a proxy command is being used to access cluster instances
(for example, when using namespaces or when specifying a custom proxy
command), rootwrap functionality is provided to allow users other than
``root`` access to the needed operating system facilities. To use rootwrap
the following configuration parameter is required to be set:

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
set the following parameter in your sahara configuration file:

.. sourcecode:: cfg

    [DEFAULT]
    rootwrap_command='sudo sahara-rootwrap /etc/sahara/rootwrap.conf'

For more information on rootwrap please refer to the
`official Rootwrap documentation <https://wiki.openstack.org/wiki/Rootwrap>`_

External key manager usage (EXPERIMENTAL)
-----------------------------------------

Sahara generates and stores several passwords during the course of operation.
To harden sahara's usage of passwords it can be instructed to use an
external key manager for storage and retrieval of these secrets. To enable
this feature there must first be an OpenStack Key Manager service deployed
within the stack. Currently, the barbican project is the only key manager
supported by sahara.

With a Key Manager service deployed on the stack, sahara must be configured
to enable the external storage of secrets. This is accomplished by editing
the configuration file as follows:

.. sourcecode:: cfg

    [DEFAULT]
    use_external_key_manager=True

.. TODO (mimccune)
    this language should be removed once a new keystone authentication
    section has been created in the configuration file.

Additionally, at this time there are two more values which must be provided
to ensure proper access for sahara to the Key Manager service. These are
the Identity domain for the administrative user and the domain for the
administrative project. By default these values will appear as:

.. sourcecode:: cfg

    [DEFAULT]
    admin_user_domain_name=default
    admin_project_domain_name=default

With all of these values configured and the Key Manager service deployed,
sahara will begin storing its secrets in the external manager.
