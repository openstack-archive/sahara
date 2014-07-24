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

1) OpenStack IceHouse installed.

2) Sahara installed, configured and running, see :doc:`/userdoc/installation.guide`.

2. Sahara Dashboard Installation
--------------------------------

1) Go to the machine where Dashboard resides and install Sahara UI there:

   For RDO:

.. sourcecode:: console

    $ sudo yum install python-django-sahara
..

   Otherwise:

.. sourcecode:: console

    $ sudo pip install sahara-dashboard
..

   This will install the latest stable release of Sahara UI. If you
   want to install the development version of Sahara UI do the
   following instead:

.. sourcecode:: console

    $ sudo pip install http://tarballs.openstack.org/sahara-dashboard/sahara-dashboard-master.tar.gz
..

   Note that dev version might be broken at any time and also it
   might lose backward compatibility with Icehouse release at some point.

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

   Note: ``settings.py`` file is located in
   ``/usr/share/openstack-dashboard/openstack_dashboard/`` by default.

3) Now let's switch to another file - ``local_settings.py``.
   If you are using Neutron instead of Nova-Network add the following
   parameter there:

.. sourcecode:: python

   SAHARA_USE_NEUTRON = True
..

   If you are using Nova-Network with ``auto_assign_floating_ip=False`` or Neutron add
   the following parameter:

.. sourcecode:: python

   AUTO_ASSIGNMENT_ENABLED = False
..

   Note: For RDO, the ``local_settings.py`` file is named
   ``local_settings`` and its absolute path is
   ``/etc/openstack-dashboard/local_settings``, otherwise the file's
   absolute path is
   ``/usr/share/openstack-dashboard/openstack_dashboard/local/local_settings.py``.

4) You also need to tell Sahara UI where it can find Sahara service.
   There are two ways to do that. First is to define Sahara endpoint in
   Keystone. The endpoint type must be ``data_processing``:

.. sourcecode:: console

    keystone service-create --name sahara --type data_processing \
        --description "Sahara Data Processing"

    keystone endpoint-create --service sahara --region RegionOne \
        --publicurl "http://10.0.0.2:8386/v1.1/%(tenant_id)s" \
        --adminurl "http://10.0.0.2:8386/v1.1/%(tenant_id)s" \
        --internalurl "http://10.0.0.2:8386/v1.1/%(tenant_id)s"
..

   While executing the commands above, don't forget to change IP
   addresses and ports to the ones actual for your setup.

   This approach might not work for you if your Keystone already has Sahara
   endpoint registered. This could be in DevStack and Fuel environments
   as both are capable to install Sahara and Sahara UI on their own. In
   that case use the second approach described below.

   The second way to tell Sahara UI where Sahara service is deployed
   is to specify ``SAHARA_URL`` parameter in ``local_settings.py``.
   For example:

.. sourcecode:: python

    SAHARA_URL = 'http://localhost:8386/v1.1'
..

5) The installation is complete. You need to restart the apache
   web server for the changes to take effect.

   For Ubuntu:

.. sourcecode:: console

    $ sudo service apache2 restart
..

   For Centos:

.. sourcecode:: console

    $ sudo service httpd reload
..

   Now if you log into Horizon you should see the Sahara menu available there.
