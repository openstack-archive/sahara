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
