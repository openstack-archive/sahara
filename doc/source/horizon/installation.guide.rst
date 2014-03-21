Sahara UI Installation Guide
============================

Sahara UI is a plugin for OpenStack Dashboard. There are two ways to install
it. One is to plug it into existing Dashboard installation and another is
to setup another Dashboard and plug Sahara UI there. The first approach
advantage is that you will have Sahara UI in the very same Dashboard with
which you work with OpenStack. The disadvantage is that you have to tweak
your Dashboard configuration in order to enable the plugin. The second
approach does not have this disadvantage.

Further steps describe installation for the first approach. For the second
approach see :doc:`/horizon/dev.environment.guide`

1. Prerequisites
----------------

1) OpenStack environment (Folsom, Grizzly or Havana version) installed.

2) Sahara installed, configured and running, see :doc:`/userdoc/installation.guide`.

2. Sahara Dashboard Installation
---------------------------------

1) Go to the machine where Dashboard resides and install Sahara UI:

   For RDO:

.. sourcecode:: console

    $ sudo yum install python-django-savanna
..

   Otherwise:

.. sourcecode:: console

    $ sudo pip install sahara-dashboard
..

   This will install latest stable release of Sahara UI. If you want to install master branch of Sahara UI:

.. sourcecode:: console

    $ sudo pip install 'http://tarballs.openstack.org/sahara-dashboard/sahara-dashboard-master.tar.gz'

2) Configure OpenStack Dashboard. In ``settings.py`` add sahara to

.. sourcecode:: python

    HORIZON_CONFIG = {
        'dashboards': ('nova', 'syspanel', 'settings', ..., 'sahara'),
..

   and also add saharadashboard to

.. sourcecode:: python

    INSTALLED_APPS = (
        'saharadashboard',
        ....
..

   Note: ``settings.py`` file is located in ``/usr/share/openstack-dashboard/openstack_dashboard/`` by default.

3) Also you have to specify **SAHARA_URL** in local_settings.py. For example:

.. sourcecode:: python

    SAHARA_URL = 'http://localhost:8386/v1.1'
..

If you are using Neutron instead of Nova Network:

.. sourcecode:: python

   SAHARA_USE_NEUTRON = True
..

If you are not using nova-network with auto_assign_floating_ip=True, also set:

.. sourcecode:: python

   AUTO_ASSIGNMENT_ENABLED = False
..


   Note: For RDO, the ``local_settings.py`` file is located in
   ``/etc/openstack-dashboard/``, otherwise it is in
   ``/usr/share/openstack-dashboard/openstack_dashboard/local/``.

4) Now all installations are done and apache web server can be restarted for the changes to take effect:

   For Ubuntu:

.. sourcecode:: console

    $ sudo service apache2 restart
..

   For Centos:

.. sourcecode:: console

    $ sudo service httpd reload
..


   You can check that service has been started successfully. Go to Horizon URL and if installation is correct you'll be able to see the Sahara tab.
