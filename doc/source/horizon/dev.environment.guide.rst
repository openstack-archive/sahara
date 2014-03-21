Sahara UI Dev Environment Setup
===============================

Install as a part of DevStack
-----------------------------

The easiest way to have local Sahara UI environment with DevStack is to
include Sahara component in DevStack.

.. toctree::
    :maxdepth: 1

    ../devref/devstack

After Sahara installation as a part of DevStack Horizon will contain Sahara
tab. Sahara dashboard source code will be located at
``$DEST/sahara_dashboard`` which is usually ``/opt/stack/sahara_dashboard``.


Isolated Dashboard for Sahara
-----------------------------

These installation steps suite for two purposes:
 * to setup dev environment
 * to setup isolated Dashboard for Sahara

Note that the host where you're going to perform installation has to be
able to connected to all OpenStack endpoints. You can list all available
endpoints using the following command:

.. sourcecode:: console

    $ keystone endpoint-list

1. Install prerequisites

.. sourcecode:: console

    $ sudo apt-get update
    $ sudo apt-get install git-core python-dev gcc python-setuptools python-virtualenv node-less libssl-dev

On Ubuntu 12.10 and higher you have to install the following lib as well:

.. sourcecode:: console

    $ sudo apt-get install nodejs-legacy

2. Checkout Horizon from git and switch to your version of OpenStack (stable/grizzly or stable/folsom).
Here is an example for grizzly:

.. sourcecode:: console

    $ git clone https://github.com/openstack/horizon -b stable/grizzly
..

    Then install virtual environment:

.. sourcecode:: console

    $ python tools/install_venv.py

3. Create ``local_settings.py`` file:

.. sourcecode:: console

    $ cp openstack_dashboard/local/local_settings.py.example openstack_dashboard/local/local_settings.py

4. Open file ``openstack_dashboard/local/local_settings.py`` and uncomment strings:

.. sourcecode:: python

   from horizon.utils import secret_key
   SECRET_KEY = secret_key.generate_or_read_....

and set right value for variables:

.. sourcecode:: python

   OPENSTACK_HOST = "ip of your controller"
   SAHARA_URL = "url for sahara (e.g. "http://localhost:8386/v1.1")"

If you are using Neutron instead of Nova Network:

.. sourcecode:: python

   SAHARA_USE_NEUTRON = True

If you are not using nova-network with auto_assign_floating_ip=True, also set:

.. sourcecode:: python

   AUTO_ASSIGNMENT_ENABLED = False
..

5. Clone sahara-dashboard sources from ``https://github.com/openstack/sahara-dashboard.git``

.. sourcecode:: console

    $ git clone https://github.com/openstack/sahara-dashboard.git

6. Export SAHARA_DASHBOARD_HOME environment variable with path to sahara-dashboard folder. E.g.:

.. sourcecode:: console

    $ export SAHARA_DASHBOARD_HOME=$(pwd)/sahara-dashboard

7. Install sahara-dashboard module to horizon's venv. Go to horizon folder and execute:

.. sourcecode:: console

    $ .venv/bin/pip install $SAHARA_DASHBOARD_HOME

8. Create a symlink to sahara-dashboard source

.. sourcecode:: console

   $ ln -s $SAHARA_DASHBOARD_HOME/saharadashboard .venv/lib/python2.7/site-packages/saharadashboard

9. In ``openstack_dashboard/settings.py`` add sahara to

.. sourcecode:: python

    HORIZON_CONFIG = {
        'dashboards': ('nova', 'syspanel', 'settings', 'sahara'),

and add saharadashboard to

.. sourcecode:: python

    INSTALLED_APPS = (
        'saharadashboard',
        ....

10. Start horizon

.. sourcecode:: console

    $ tools/with_venv.sh python manage.py runserver 0.0.0.0:8080

This will start horizon in debug mode. That means the logs will be written to console,
and if any exceptions happen, you will see the stack-trace rendered as a web-page.

The debug could be disabled by changing ``DEBUG=True`` to ``False`` in
``local_settings.py``. In that case Horizon should be started slightly
differently, otherwise it will not serve static files:

.. sourcecode:: console

    $ tools/with_venv.sh  python manage.py runserver --insecure 0.0.0.0:8080

It is not recommended to use horizon in this mode for production.

11. Applying changes

If you have changed any ``*.py`` files in ``$SAHARA_DASHBOARD_HOME`` directory,
horizon will notice that and reload automatically.
However changes made to non-python files may not be noticed,
so you have to restart horizon again manually, as described in step 10.
