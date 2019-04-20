Sahara UI Dev Environment Setup
===============================

This page describes how to setup Horizon for developing Sahara by either
installing it as part of DevStack with Sahara or installing it in an
isolated environment and running from the command line.

Install as a part of DevStack
-----------------------------

See the `DevStack guide <devstack.html>`_ for more information
on installing and configuring DevStack with Sahara.

Sahara UI can be installed as a DevStack plugin by adding the following line
to your ``local.conf`` file

.. sourcecode:: bash

    # Enable sahara-dashboard
    enable_plugin sahara-dashboard https://opendev.org/openstack/sahara-dashboard


Isolated Dashboard for Sahara
-----------------------------

These installation steps serve two purposes:
 1. Setup a dev environment
 2. Setup an isolated Dashboard for Sahara

**Note** The host where you are going to perform installation has to be able
to connect to all OpenStack endpoints. You can list all available endpoints
using the following command:

.. sourcecode:: console

    $ openstack endpoint list

You can list the registered services with this command:

.. sourcecode:: console

    $ openstack service list

Sahara service should be present in keystone service list with service type
*data-processing*

1. Install prerequisites

.. sourcecode:: console

    $ sudo apt-get update
    $ sudo apt-get install git-core python-dev gcc python-setuptools \
              python-virtualenv node-less libssl-dev libffi-dev libxslt-dev
..

On Ubuntu 12.10 and higher you have to install the following lib as well:

.. sourcecode:: console

    $ sudo apt-get install nodejs-legacy
..

2. Checkout Horizon from git and switch to your version of OpenStack

Here is an example:

.. sourcecode:: console

    $ git clone https://opendev.org/openstack/horizon/ {HORIZON_DIR}
..

Then install the virtual environment:

.. sourcecode:: console

    $ python {HORIZON_DIR}/tools/install_venv.py
..

3. Create a ``local_settings.py`` file

.. sourcecode:: console

    $ cp {HORIZON_DIR}/openstack_dashboard/local/local_settings.py.example \
               {HORIZON_DIR}/openstack_dashboard/local/local_settings.py
..

4. Modify ``{HORIZON_DIR}/openstack_dashboard/local/local_settings.py``

Set the proper values for host and url variables:

.. sourcecode:: python

    OPENSTACK_HOST = "ip of your controller"
..

If you wish to disable floating IP options during node group template
creation, add the following parameter:

.. sourcecode:: python

    SAHARA_FLOATING_IP_DISABLED = True
..

5. Clone sahara-dashboard repository and checkout the desired branch

.. sourcecode:: console

    $ git clone https://opendev.org/openstack/sahara-dashboard/ \
        {SAHARA_DASHBOARD_DIR}
..

6. Copy plugin-enabling files from sahara-dashboard repository to horizon

.. sourcecode:: console

    $ cp -a {SAHARA_DASHBOARD_DIR}/sahara_dashboard/enabled/* {HORIZON_DIR}/openstack_dashboard/local/enabled/
..

7. Install sahara-dashboard project into your horizon virtualenv
   in editable mode

.. sourcecode:: console

    $ . {HORIZON_DIR}/.venv/bin/activate
    $ pip install -e {SAHARA_DASHBOARD_DIR}
..

8. Start Horizon

.. sourcecode:: console

    $ . {HORIZON_DIR}/.venv/bin/activate
    $ python {HORIZON_DIR}/manage.py runserver 0.0.0.0:8080
..

This will start Horizon in debug mode. That means the logs will be written to
console and if any exceptions happen, you will see the stack-trace rendered
as a web-page.

Debug mode can be disabled by changing ``DEBUG=True`` to ``False`` in
``local_settings.py``. In that case Horizon should be started slightly
differently, otherwise it will not serve static files:

.. sourcecode:: console

    $ . {HORIZON_DIR}/.venv/bin/activate
    $ python {HORIZON_DIR}/manage.py runserver --insecure 0.0.0.0:8080
..

.. note::

    It is not recommended to use Horizon in this mode for production.

