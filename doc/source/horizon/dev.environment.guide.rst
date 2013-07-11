Savanna Horizon Plugin dev environment setup
============================================

1. Install prerequisites

.. sourcecode:: console

    $ sudo apt-get update
    $ sudo apt-get install git python-dev gcc python-setuptools python-virtualenv node-less

On Ubuntu 12.10 and higher you have to install the following lib as well:

.. sourcecode:: console

    $ sudo apt-get install nodejs-legacy

2. Checkout stable horizon from git `https://github.com/openstack/horizon.git` according to your version of OpenStack (stable/grizzly or stable/folsom) and install venv

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

   OPENSTACK_HOST = "your ip of controller"
   SAVANNA_URL = "url for savanna (e.g. "http://localhost:8386/v1.0")"

5. Install savanna-dashboard module to horizon's venv:

.. sourcecode:: console

    $ .venv/bin/python $SAVANNA_DASHBOARD_HOME/setup.py install

6. Create a symlink to

.. sourcecode:: console

   $ ln -s $SAVANNA_DASHBOARD_HOME/savannadashboard .venv/lib/python2.7/site-packages/savannadashboard

7. In ``openstack_dashboard/settings.py`` add savanna to

.. sourcecode:: python

    HORIZON_CONFIG = {
        'dashboards': ('nova', 'syspanel', 'settings', 'savanna'),

and add savannadashboard to

.. sourcecode:: python

    INSTALLED_APPS = (
        'savannadashboard',
        ....

8. Start horizon

.. sourcecode:: console

    $ tools/with_venv.sh  python manage.py runserver 0.0.0.0:8080

This will start horizon in debug mode. That means the logs will be written to console,
and if any exceptions happen, you will see the stack-trace rendered as a web-page.

It is not recommended to use horizon in this mode for production.

9. Applying changes

If you have changed any ``*.py`` files in ``$SAVANNA_DASHBOARD_HOME`` directory,
horizon will notice that and reload automatically.
However changes made to non-python files may not be noticed,
so you have to start horizon again manually, as described in step 8.
