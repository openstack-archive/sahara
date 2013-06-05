Savanna Horizon Plugin dev environment setup
============================================

1. Install nodejs 0.10.10

2. Checkout stable horizon from git git@github.com:openstack/horizon.git according to your version of OpenStack (stable/grizzly or stable/folsom) and install venv

.. sourcecode:: bash

   python tools/install_venv.py

3. Edit file open openstack_dashboard/local/local_settings.py and uncomment strings:

.. sourcecode:: python

   from horizon.utils import secret_key
   SECRET_KEY = secret_key.generate_or_read_....

and set right value for variable

.. sourcecode:: python

   OPENSTACK_HOST

4. Create a symlink to

.. sourcecode:: bash

   ln -s $SAVANNA_DASHBOARD_HOME/savannadashboard .venv/lib/python2.7/site-packages/savannadashboard

5. In openstack_dashboard/settings.py add savanna to

.. sourcecode:: python

    HORIZON_CONFIG = {
        'dashboards': ('nova', 'syspanel', 'settings', 'savanna'),

and add savannadashboard to

.. sourcecode:: python

    INSTALLED_APPS = (
        'savannadashboard',
        ....

6. Start horizon

.. sourcecode:: bash

    tools/with_venv.sh  python manage.py runserver 0.0.0.0:8080