Savanna UI Dev Environment Setup
============================================

These installation steps suite for two purposes:
 * to setup dev environment
 * to setup isolated Dashboard for Savanna

Note that the host where you're going to perform installation has to be
able to connected to all OpenStack endpoints. You can list all available
endpoints using the following command:

.. sourcecode:: console

    $ keystone endpoint-list

1. Install prerequisites

.. sourcecode:: console

    $ sudo apt-get update
    $ sudo apt-get install git-core python-dev gcc python-setuptools python-virtualenv node-less

   On Ubuntu 12.10 and higher you have to install the following lib as well:

.. sourcecode:: console

    $ sudo apt-get install nodejs-legacy

2. Checkout Horizon from git and switch to your version of OpenStack (stable/grizzly or stable/folsom).
Here is an example for grizzly:

.. sourcecode:: console

    $ git clone https://github.com/openstack/horizon
    $ git checkout -b stable/grizzly origin/stable/grizzly
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
   SAVANNA_URL = "url for savanna (e.g. "http://localhost:8386/v1.0")"

5. Clone savanna-dashboard sources from ``https://github.com/stackforge/savanna-dashboard.git``

.. sourcecode:: console

    $ git clone https://github.com/stackforge/savanna-dashboard.git

6. Export SAVANNA_DASHBOARD_HOME environment variable with path to savanna-dashboard folder. E.g.:

.. sourcecode:: console

    $ export SAVANNA_DASHBOARD_HOME=$(pwd)/savanna-dashboard

7. Install savanna-dashboard module to horizon's venv. Go to horizon folder and execute:

.. sourcecode:: console

    $ .venv/bin/python $SAVANNA_DASHBOARD_HOME/setup.py install

8. Create a symlink to savannadashboard source

.. sourcecode:: console

   $ ln -s $SAVANNA_DASHBOARD_HOME/savannadashboard .venv/lib/python2.7/site-packages/savannadashboard

9. In ``openstack_dashboard/settings.py`` add savanna to

.. sourcecode:: python

    HORIZON_CONFIG = {
        'dashboards': ('nova', 'syspanel', 'settings', 'savanna'),

and add savannadashboard to

.. sourcecode:: python

    INSTALLED_APPS = (
        'savannadashboard',
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

If you have changed any ``*.py`` files in ``$SAVANNA_DASHBOARD_HOME`` directory,
horizon will notice that and reload automatically.
However changes made to non-python files may not be noticed,
so you have to restart horizon again manually, as described in step 10.
