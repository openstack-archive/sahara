Sahara Configuration Guide
==========================

This guide covers the steps for a basic configuration of sahara.
It will help you to configure the service in the most simple
manner.

Basic configuration
-------------------

A full configuration file showing all possible configuration options and their
defaults can be generated with the following command:

.. sourcecode:: cfg

    $ tox -e genconfig

Running this command will create a file named ``sahara.conf.sample``
in the ``etc/sahara`` directory of the project.

After creating a configuration file by either generating one or starting with
an empty file, edit the ``connection`` parameter in the
``[database]`` section. The URL provided here should point to an empty
database. For example, the connection string for a MySQL database will be:

.. sourcecode:: cfg

    connection=mysql+pymsql://username:password@host:port/database

Next you will configure the Identity service parameters in the
``[keystone_authtoken]`` section. The ``www_authenticate_uri`` parameter
should point to the public Identity API endpoint. The ``auth_url``
should point to the internal Identity API endpoint. For example:

.. sourcecode:: cfg

    www_authenticate_uri=http://127.0.0.1:5000/v3/
    auth_url=http://127.0.0.1:5000/v3/

Specify the ``username``, ``user_domain_name``, ``password``, ``project_name``.
and ``project_domain_name``. These parameters must specify an Identity user who
has the ``admin`` role in the given project. These credentials allow sahara to
authenticate and authorize its users.

Next you will configure the default Networking service. If using
neutron for networking the following parameter should be set
in the ``[DEFAULT]`` section:

With these parameters set, sahara is ready to run.

By default the sahara's log level is set to INFO. If you wish to increase
the logging levels for troubleshooting, set ``debug`` to ``true`` in the
``[DEFAULT]`` section of the configuration file.

Networking configuration
------------------------

By default sahara is configured to use the neutron. Additionally, if the
cluster supports network namespaces the ``use_namespaces`` property can
be used to enable their usage.

.. sourcecode:: cfg

    [DEFAULT]
    use_namespaces=True

.. note::
    If a user other than ``root`` will be running the Sahara server
    instance and namespaces are used, some additional configuration is
    required, please see :ref:`non-root-users` for more information.

.. _floating_ip_management:

Floating IP management
++++++++++++++++++++++

During cluster setup sahara must access instances through a secure
shell (SSH). To establish this connection it may use either the fixed
or floating IP address of an instance. By default sahara is configured
to use floating IP addresses for access. This is controlled by the
``use_floating_ips`` configuration parameter. With this setup the user
has two options for ensuring that the instances in the node groups
templates that requires floating IPs gain a floating IP address:

* The user may specify a floating IP address pool for each node
  group that requires floating IPs directly.

From Newton changes were made to allow the coexistence of clusters using
floating IPs and clusters using fixed IPs. If ``use_floating_ips`` is
True it means that the floating IPs can be used by Sahara to spawn clusters.
But, differently from previous versions, this does not mean that all
instances in the cluster must have floating IPs and that all clusters
must use floating IPs. It is possible in a single Sahara deploy to have
clusters setup using fixed IPs, clusters using floating IPs and cluster that
use both.

If not using floating IP addresses (``use_floating_ips=False``) sahara
will use fixed IP addresses for instance management. When using neutron
for the Networking service the user will be able to choose the
fixed IP network for all instances in a cluster.

.. _notification-configuration:

Notifications configuration
---------------------------

Sahara can be configured to send notifications to the OpenStack
Telemetry module. To enable this functionality the following parameter
``enable`` should be set in the ``[oslo_messaging_notifications]`` section
of the configuration file:

.. sourcecode:: cfg

    [oslo_messaging_notifications]
    enable = true

And the following parameter ``driver`` should be set in the
``[oslo_messaging_notifications]`` section of the configuration file:

.. sourcecode:: cfg

    [oslo_messaging_notifications]
    driver = messaging

By default sahara is configured to use RabbitMQ as its message broker.

If you are using RabbitMQ as the message broker, then you should set the
following parameter in the ``[DEFAULT]`` section:

.. sourcecode:: cfg

    rpc_backend = rabbit

You may also need to specify the connection parameters for your
RabbitMQ installation. The following example shows the default
values in the ``[oslo_messaging_rabbit]`` section which may need
adjustment:

.. sourcecode:: cfg

    rabbit_host=localhost
    rabbit_port=5672
    rabbit_hosts=$rabbit_host:$rabbit_port
    rabbit_userid=guest
    rabbit_password=guest
    rabbit_virtual_host=/
..

.. _orchestration-configuration:

Orchestration configuration
---------------------------

By default sahara is configured to use the heat engine for instance
creation. The heat engine uses the OpenStack Orchestration service to
provision instances. This engine makes calls directly to the services required
for instance provisioning.

.. _policy-configuration-label:

Policy configuration
--------------------

.. warning::

   JSON formatted policy file is deprecated since Sahara 15.0.0 (Xena).
   This `oslopolicy-convert-json-to-yaml`__ tool will migrate your existing
   JSON-formatted policy file to YAML in a backward-compatible way.

.. __: https://docs.openstack.org/oslo.policy/victoria/cli/oslopolicy-convert-json-to-yaml.html

Sahara's public API calls may be restricted to certain sets of users by
using a policy configuration file. The location of the policy file(s)
is controlled by the ``policy_file`` and ``policy_dirs`` parameters
in the ``[oslo_policy]`` section. By default sahara will search for
a ``policy.yaml`` file in the same directory as the ``sahara.conf``
configuration file.

Examples
++++++++

Example 1. Allow all method to all users (default policy).

.. sourcecode:: json

    {
        "default": ""
    }


Example 2. Disallow image registry manipulations to non-admin users.

.. sourcecode:: json

    {
        "default": "",

        "data-processing:images:register": "role:admin",
        "data-processing:images:unregister": "role:admin",
        "data-processing:images:add_tags": "role:admin",
        "data-processing:images:remove_tags": "role:admin"
    }

API configuration
-----------------

Sahara uses the ``api-paste.ini`` file to configure the data processing API
service. For middleware injection sahara uses pastedeploy library. The location
of the api-paste file is controlled by the ``api_paste_config`` parameter in
the ``[default]`` section. By default sahara will search for a
``api-paste.ini`` file in the same directory as the configuration file.
