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
