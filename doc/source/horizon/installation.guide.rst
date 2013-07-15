Savanna UI Installation Guide
=============================

Savanna UI is a plugin for OpenStack Dashboard. There are two ways to install
it. One is to plug it into existing Dashboard installation and another is
to setup another Dashboard and plug Savanna UI there. The first approach
advantage is that you will have Savanna UI in the very same Dashboard with
which you work with OpenStack. The disadvantage is that you have to tweak
your Dashboard configuration in order to enable the plugin. The second
approach does not have this disadvantage.

Further steps describe installation for the first approach. For the second
approach see :doc:`/horizon/dev.environment.guide`

1. Prerequisites
----------------

1) OpenStack environment (Folsom or Grizzly version) installed.

2) Savanna installed, configured and running.

2. Savanna Dashboard Installation
---------------------------------

1) Go to the machine where Dashboard resides and install Savanna UI:

.. sourcecode:: console

    $ sudo pip install savannadashboard
..

   This will install latest stable release of Savanna UI. If you want to install master branch of Savanna UI:

.. sourcecode:: console

    $ sudo pip install 'http://tarballs.openstack.org/savanna-dashboard/savanna-dashboard-master.tar.gz'

2) Configure OpenStack Dashboard. In ``settings.py`` add savanna to

.. sourcecode:: python

    HORIZON_CONFIG = {
        'dashboards': ('nova', 'syspanel', 'settings', 'savanna'),
..

   and also add savannadashboard to

.. sourcecode:: python

    INSTALLED_APPS = (
        'savannadashboard',
        ....
..

   Note: ``settings.py`` file is located in ``/usr/share/openstack_dashboard/openstack-dashboard/`` by default.

3) Also you have to specify **SAVANNA_URL** in local_settings.py. For example:

.. sourcecode:: python

    SAVANNA_URL = 'http://localhost:8386/v1.0'
..

   Note: ``local_settings.py`` file is located in ``/usr/share/openstack-dashboard/openstack_dashboard/local/`` by default.

4) Now all installations are done and apache web server can be restarted for the changes to take effect:

.. sourcecode:: console

    $ sudo service apache2 restart
..

   You can check that service has been started successfully. Go to Horizon URL and if installation is correct you'll be able to see the Savanna tab.
