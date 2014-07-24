Sahara UI Dev Environment Setup
===============================

This page describes how to setup the Sahara dashboard UI component by either
installing it as part of DevStack or installing it in an isolated environment
and running from the command line.

Install as a part of DevStack
-----------------------------

The easiest way to have a local Sahara UI environment with DevStack is to
include the Sahara-Dashboard component in DevStack. This can be accomplished
by modifying your DevStack ``local.conf`` file to enable ``sahara-dashboard``.
See the `DevStack documentation <http://devstack.org>`_ for more information
on installing and configuring DevStack.

If you are developing Sahara from an OSX environment you will need to run
DevStack on a virtual machine. See
`Setup VM for DevStack on OSX <../devref/devstack.html>`_ for more
information.

After Sahara-Dashboard installation as a part of DevStack, Horizon will contain
a Sahara tab. Sahara-Dashboard source code will be located at
``$DEST/sahara-dashboard`` which is usually ``/opt/stack/sahara-dashboard``.

Isolated Dashboard for Sahara
-----------------------------

These installation steps serve two purposes:
 1. Setup a dev environment
 2. Setup an isolated Dashboard for Sahara

**Note** The host where you are going to perform installation has to be able
to connect to all OpenStack endpoints. You can list all available endpoints
using the following command:

.. sourcecode:: console

    $ keystone endpoint-list

1. Install prerequisites

  .. sourcecode:: console

      $ sudo apt-get update
      $ sudo apt-get install git-core python-dev gcc python-setuptools python-virtualenv node-less libssl-dev libffi-dev
  ..

  On Ubuntu 12.10 and higher you have to install the following lib as well:

  .. sourcecode:: console

      $ sudo apt-get install nodejs-legacy
  ..

2. Checkout Horizon from git and switch to your version of OpenStack

  Here is an example for the Icehouse release:

  .. sourcecode:: console

      $ git clone https://github.com/openstack/horizon -b stable/icehouse
  ..

  Then install the virtual environment:

  .. sourcecode:: console

      $ python tools/install_venv.py
  ..

3. Create a ``local_settings.py`` file

  .. sourcecode:: console

      $ cp openstack_dashboard/local/local_settings.py.example openstack_dashboard/local/local_settings.py
  ..

4. Modify ``openstack_dashboard/local/local_settings.py``

  Set the proper values for host and url variables:

  .. sourcecode:: python

     OPENSTACK_HOST = "ip of your controller"
     SAHARA_URL = "url for sahara (e.g. "http://localhost:8386/v1.1")"
  ..

  If you are using Neutron instead of Nova-Network:

  .. sourcecode:: python

     SAHARA_USE_NEUTRON = True
  ..

  If you are using Nova-Network with ``auto_assign_floating_ip=False`` or Neutron add
  the following parameter:

  .. sourcecode:: python

     AUTO_ASSIGNMENT_ENABLED = False
  ..

5. Clone sahara-dashboard sources from ``https://github.com/openstack/sahara-dashboard.git``

  .. sourcecode:: console

      $ git clone https://github.com/openstack/sahara-dashboard.git
  ..

6. Export SAHARA_DASHBOARD_HOME environment variable with a path to
   sahara-dashboard folder

  .. sourcecode:: console

      $ export SAHARA_DASHBOARD_HOME=$(pwd)/sahara-dashboard
  ..

7. Create a symlink to sahara-dashboard source

  .. sourcecode:: console

     $ ln -s $SAHARA_DASHBOARD_HOME/saharadashboard .venv/lib/python2.7/site-packages/saharadashboard
  ..

8. Install python-saharaclient into venv

  .. sourcecode:: console

     $ .venv/bin/pip install python-saharaclient
  ..

9. Modify ``openstack_dashboard/settings.py``

  Add sahara to to the Horizon config:

  .. sourcecode:: python

      HORIZON_CONFIG = {
          'dashboards': ('nova', 'syspanel', 'settings', 'sahara'),
  ..

  and add saharadashboard to the installed apps:

  .. sourcecode:: python

      INSTALLED_APPS = (
          'saharadashboard',
          ....
  ..

10. Start Horizon

  .. sourcecode:: console

      $ tools/with_venv.sh python manage.py runserver 0.0.0.0:8080
  ..

  This will start Horizon in debug mode. That means the logs will be written to console
  and if any exceptions happen, you will see the stack-trace rendered as a web-page.

  Debug mode can be disabled by changing ``DEBUG=True`` to ``False`` in
  ``local_settings.py``. In that case Horizon should be started slightly
  differently, otherwise it will not serve static files:

  .. sourcecode:: console

      $ tools/with_venv.sh  python manage.py runserver --insecure 0.0.0.0:8080
  ..

  **Note** It is not recommended to use Horizon in this mode for production.

11. Applying changes

  If you have changed any ``*.py`` files in ``$SAHARA_DASHBOARD_HOME`` directory,
  Horizon will notice that and reload automatically. However changes made to
  non-python files may not be noticed, so you have to restart Horizon again
  manually, as described in step 10.
