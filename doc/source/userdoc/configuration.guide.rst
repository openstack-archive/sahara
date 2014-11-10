Sahara Configuration Guide
==========================

This guide covers steps for basic configuration of Sahara.
It will help you to configure the service in the most simple manner.

Let's start by configuring Sahara server. The server is packaged
with two sample config files: ``sahara.conf.sample-basic`` and
``sahara.conf.sample``. The former contains all essential parameters,
while the later contains the full list. We recommend to create your config
based on the basic sample, as most probably changing parameters listed here
will be enough.

First, edit ``connection`` parameter in the ``[database]`` section. The URL
provided here should point to an empty database. For instance, connection
string for mysql database will be:

.. sourcecode:: cfg

    connection=mysql://username:password@host:port/database
..

Switch to the ``[keystone_authtoken]`` section. The ``auth_uri`` parameter
should point to the public Identity API endpoint. ``identity_uri`` should
point to the admin Identity API endpoint. For example:

.. sourcecode:: cfg

    auth_uri=http://127.0.0.1:5000/v2.0/
    identity_uri=http://127.0.0.1:35357/
..

Next specify ``admin_user``, ``admin_password`` and
``admin_tenant_name``. These parameters must specify a keystone user
which has the ``admin`` role in the given tenant. These credentials allow
Sahara to authenticate and authorize its users.

Switch to the ``[DEFAULT]`` section.  Proceed to the networking parameters.
If you are using Neutron for networking, then set

.. sourcecode:: cfg

    use_neutron=true
..

Otherwise if you are using Nova-Network set the given parameter to false.

That should be enough for the first run. If you want to increase logging
level for troubleshooting, there are two parameters in the config:
``verbose`` and ``debug``. If the former is set to true, Sahara will start
to write logs of INFO level and above. If ``debug`` is set to true,
Sahara will write all the logs, including the DEBUG ones.

Sahara notifications configuration
----------------------------------

Sahara can send notifications to Ceilometer, if it's enabled.
If you want to enable notifications you should switch to ``[DEFAULT]``
section and set:

.. sourcecode:: cfg

    enable_notifications = true
    notification_driver = messaging
..

The current default for Sahara is to use the backend that utilizes RabbitMQ
as the message broker. You should configure your backend. It's recommended to use
Rabbit or Qpid.

If you are using Rabbit as a backend, then you should set:

.. sourcecode:: cfg

    rpc_backend = rabbit
..

And after that you should specify following options:
``rabbit_host``, ``rabbit_port``, ``rabbit_userid``,
``rabbit_password``, ``rabbit_virtual_host`` and ``rabbit_hosts``.

As example you can see default values of these options:

.. sourcecode:: cfg

    rabbit_host=localhost
    rabbit_port=5672
    rabbit_hosts=$rabbit_host:$rabbit_port
    rabbit_userid=guest
    rabbit_password=guest
    rabbit_virtual_host=/
..

If you are using Qpid as backend, then you should set:

.. sourcecode:: cfg

    rpc_backend = qpid
..

And after that you should specify following options:
``qpid_hostname``, ``qpid_port``, ``qpid_username``,
``qpid_password`` and ``qpid_hosts``.

As example you can see default values of these options:

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

Sahara’s public API calls may be restricted to certain sets of users using a
policy configuration file. Location of policy file is controlled by
``policy_file`` and ``policy_dirs`` parameters. By default Sahara will search
for ``policy.json`` file in the same directory where Sahara configuration is
located.

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