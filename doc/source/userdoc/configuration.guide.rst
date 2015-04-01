Sahara Configuration Guide
==========================

This guide covers the steps for a basic configuration of sahara.
It will help you to configure the service in the most simple
manner.

Sahara is packaged with a basic sample configration file:
``sahara.conf.sample-basic``. This file contains all the essential
parameters that are required for sahara. We recommend creating your
configuration file based on this basic example.

If a more thorough configuration is needed we recommend using the ``tox``
tool to create a full configuration file by executing the following
command:

.. sourcecode:: cfg

    $ tox -e genconfig

..

Running this command will create a file named ``sahara.conf.sample``
in the ``etc/sahara`` directory of the project.

After creating a configuration file by either copying the basic example
or generating one, edit the ``connection`` parameter in the
``[database]`` section. The URL provided here should point to an empty
database. For example, the connection string for a MySQL database will be:

.. sourcecode:: cfg

    connection=mysql://username:password@host:port/database
..

Next you will configure the Identity service parameters in the
``[keystone_authtoken]`` section. The ``auth_uri`` parameter
should point to the public Identity API endpoint. The ``identity_uri``
should point to the admin Identity API endpoint. For example:

.. sourcecode:: cfg

    auth_uri=http://127.0.0.1:5000/v2.0/
    identity_uri=http://127.0.0.1:35357/
..

Specify the ``admin_user``, ``admin_password`` and ``admin_tenant_name``.
These parameters must specify an Identity user who has the ``admin`` role
in the given tenant. These credentials allow sahara to authenticate and
authorize its users.

Next you will configure the default Networking service. If using
neutron for networking the following parameter should be set
in the ``[DEFAULT]`` section:

.. sourcecode:: cfg

    use_neutron=true
..

If you are using nova-network for networking then this parameter should
be set to ``false``.

With these paramaters set, sahara is ready to run.

If you wish to increase the logging levels for troubleshooting there
are two parameters in the ``[DEFAULT]`` section of the configuration
file which control the level of logging output; ``verbose`` and
``debug``. With ``verbose`` set to ``true`` sahara's default logging
level will be set to INFO, and with ``debug`` set to ``true`` it will
be set to DEBUG. By default the sahara's log level is set to WARNING.

Sahara notifications configuration
----------------------------------

Sahara can be configured to send notifications to the OpenStack
Telemetry module. To enable this functionality the following parameters
should be set in the ``[DEFAULT]`` section of the configuration file:

.. sourcecode:: cfg

    enable_notifications = true
    notification_driver = messaging
..

By default sahara is configured to use RabbitMQ as its message broker,
but it can be configured to use Qpid instead if needed.

If you are using RabbitMQ as the message broker, then you should set the
following parameter in the ``[DEFAULT]`` section:

.. sourcecode:: cfg

    rpc_backend = rabbit
..

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

If you are using Qpid as the message broker, then you should
set the ``rpc_backend`` as follows:

.. sourcecode:: cfg

    rpc_backend = qpid
..

You may also need to adjust the following default connection parameters
in the ``[oslo_messaging_qpid]`` section:

.. sourcecode:: cfg

    qpid_hostname=localhost
    qpid_port=5672
    qpid_hosts=$qpid_hostname:$qpid_port
    qpid_username=
    qpid_password=
..

.. _policy-configuration-label:

Sahara policy configuration
---------------------------

Sahara’s public API calls may be restricted to certain sets of users by
using a policy configuration file. The location of the policy file(s)
is controlled by the ``policy_file`` and ``policy_dirs`` parameters
in the ``[DEFAULT]`` section. By default sahara will search for
a ``policy.json`` file in the same directory as the configuration file.

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

        "images:register": "role:admin",
        "images:unregister": "role:admin",
        "images:add_tags": "role:admin",
        "images:remove_tags": "role:admin"
    }
