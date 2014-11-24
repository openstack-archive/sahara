Sahara Installation Guide
=========================

We recommend to install Sahara in a way that will keep your system in a
consistent state. We suggest the following options:

* Install via `Fuel <http://fuel.mirantis.com/>`_

* Install via `RDO Havana+ <http://openstack.redhat.com/>`_

* Install into virtual environment



To install with Fuel
--------------------

1. Start by following the `MOS Quickstart
   <http://software.mirantis.com/quick-start/>`_ to install and setup
   OpenStack.

2. Enable Sahara service during installation.



To install with RDO
-------------------

1. Start by following the `RDO Quickstart
   <http://openstack.redhat.com/Quickstart>`_ to install and setup
   OpenStack.

2. Install Sahara:

.. sourcecode:: console

    # yum install openstack-sahara
..

3. Configure Sahara as needed. The configuration file is located in
   ``/etc/sahara/sahara.conf``. For details see
   :doc:`Sahara Configuration Guide <configuration.guide>`

4. Create database schema:

.. sourcecode:: console

    # sahara-db-manage --config-file /etc/sahara/sahara.conf upgrade head
..

5. Go through :ref:`common_installation_steps` and make the
   necessary changes.

6. Start the sahara-all service:

.. sourcecode:: console

    # systemctl start openstack-sahara-all
..

7. *(Optional)* Enable Sahara to start on boot

.. sourcecode:: console

    # systemctl enable openstack-sahara-all
..


To install into a virtual environment
-------------------------------------

1. First you need to install a number of packages with your
   OS package manager. The list of packages depends on the OS you use.
   For Ubuntu run:

.. sourcecode:: console

    $ sudo apt-get install python-setuptools python-virtualenv python-dev
..

   For Fedora:

.. sourcecode:: console

    $ sudo yum install gcc python-setuptools python-virtualenv python-devel
..

   For CentOS:

.. sourcecode:: console

    $ sudo yum install gcc python-setuptools python-devel
    $ sudo easy_install pip
    $ sudo pip install virtualenv

2. Setup virtual environment for Sahara:

.. sourcecode:: console

    $ virtualenv sahara-venv
..

   This will install python virtual environment into ``sahara-venv`` directory
   in your current working directory. This command does not require super
   user privileges and could be executed in any directory current user has
   write permission.

3. You can install the latest Sahara release from pypi:

.. sourcecode:: console

    $ sahara-venv/bin/pip install sahara
..

   Or you can get Sahara archive from `<http://tarballs.openstack.org/sahara/>`_ and install it using pip:

.. sourcecode:: console

    $ sahara-venv/bin/pip install 'http://tarballs.openstack.org/sahara/sahara-master.tar.gz'
..

   Note that sahara-master.tar.gz contains the latest changes and might not be stable at the moment.
   We recommend browsing `<http://tarballs.openstack.org/sahara/>`_ and selecting the latest stable release.

4. After installation you should create configuration file from a sample
   config located in ``sahara-venv/share/sahara/sahara.conf.sample-basic``:

.. sourcecode:: console

    $ mkdir sahara-venv/etc
    $ cp sahara-venv/share/sahara/sahara.conf.sample-basic sahara-venv/etc/sahara.conf
..

    Make the necessary changes in ``sahara-venv/etc/sahara.conf``.
    For details see :doc:`Sahara Configuration Guide <configuration.guide>`

.. _common_installation_steps:

Common installation steps
-------------------------

The steps below are common for both installing Sahara as part of RDO and
installing it in virtual environment.

1. If you use Sahara with MySQL database, then for storing big Job Binaries
   in Sahara Internal Database you must configure size of max allowed packet.
   Edit ``my.cnf`` and change parameter:

.. sourcecode:: ini

   ...
   [mysqld]
   ...
   max_allowed_packet          = 256M
..

    and restart mysql server.

2. Create database schema:

.. sourcecode:: console

    $ sahara-venv/bin/sahara-db-manage --config-file sahara-venv/etc/sahara.conf upgrade head
..

3. To start Sahara call:

.. sourcecode:: console

    $ sahara-venv/bin/sahara-all --config-file sahara-venv/etc/sahara.conf
..

.. _register-sahara-label:

4. In order for Sahara to be accessible in OpenStack Dashboard and for
   python-saharaclient to work properly you need to register Sahara in
   Keystone. For example:

.. sourcecode:: console

    keystone service-create --name sahara --type data-processing \
        --description "Sahara Data Processing"

    keystone endpoint-create --service sahara --region RegionOne \
        --publicurl "http://10.0.0.2:8386/v1.1/%(tenant_id)s" \
        --adminurl "http://10.0.0.2:8386/v1.1/%(tenant_id)s" \
        --internalurl "http://10.0.0.2:8386/v1.1/%(tenant_id)s"
..

5. To adjust OpenStack Dashboard configuration with your Sahara installation
   please follow the UI configuration guide :doc:`here. <dashboard.guide>`

Notes:
------

Make sure that your operating system is not blocking Sahara port (default: 8386).
You may need to configure iptables in CentOS and some other operating systems.


To get the list of all possible options run:

.. sourcecode:: console

    $ sahara-venv/bin/python sahara-venv/bin/sahara-all --help
..


Further consider reading :doc:`overview` for general Sahara concepts and
:doc:`plugins` for specific plugin features/requirements.
