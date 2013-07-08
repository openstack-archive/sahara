Savanna Dashboard Setup
=======================

1 Setup prerequisites
---------------------

1.1 OpenStack environment (Folsom or Grizzly version) installed.

1.2 Savanna REST API service installed, configured and running.

1.3 Operating system, where OpenStack Dashboard service installed, has to be connected to internal OpenStack network.

2 Savanna Dashboard Installation
--------------------------------

2.1 Go to your Horizon’s machine and install Savanna Dashboard:

.. sourcecode:: bash

    sudo pip install savannadashboard

This will install latest release of Savanna Dashboard. If you want to install master branch of Savanna Dashboard:

.. sourcecode:: bash

    sudo pip install http://tarballs.openstack.org/savanna-dashboard/savanna-dashboard-master.tar.gz

2.2 Configure OpenStack Dashboard

In settings.py add savanna to

.. sourcecode:: python

    HORIZON_CONFIG = {
        'dashboards': ('nova', 'syspanel', 'settings', 'savanna'),

and add savannadashboard to

.. sourcecode:: python

    INSTALLED_APPS = (
        'savannadashboard',
        ....

Note: settings.py file is located in /usr/share/openstack-dashboard by default.

Also you have to specify **SAVANNA_URL** in local_settings.py

.. sourcecode:: python

    SAVANNA_URL = "url for savanna (e.g. "http://localhost:8080/v1.0")"

Note: local_settings.py file is located in /usr/share/openstack-dashboard/local by default.

2.3 Now all installations are done and apache web server can be restarted for the changes to take effect:

.. sourcecode:: bash

    sudo service apache2 restart

You can check that service has been started successfully. Go to Horizon URL and if installation is correct you'll be able to see the Savanna tab.