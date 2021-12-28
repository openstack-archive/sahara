Sahara Installation Guide
=========================

We recommend installing sahara in a way that will keep your system in a
consistent state. We suggest the following options:

* Install via `Fuel <http://fuel.mirantis.com/>`_

* Install via :kolla-ansible-doc:`Kolla <>`

* Install via `RDO <https://www.rdoproject.org/>`_

* Install into a virtual environment



To install with Fuel
--------------------

1. Start by following the `MOS Quickstart
   <http://software.mirantis.com/quick-start/>`_ to install and setup
   OpenStack.

2. Enable the sahara service during installation.

To install with Kolla
---------------------

1. Start by following the :kolla-ansible-doc:`Kolla Quickstart
   <user/quickstart.html>`
   to install and setup OpenStack.

2. Enable the sahara service during installation.



To install with RDO
-------------------

1. Start by following the `RDO Quickstart
   <https://www.rdoproject.org/install/>`_ to install and setup
   OpenStack.

2. Install sahara:

.. sourcecode:: console

    # yum install openstack-sahara
..

3. Configure sahara as needed. The configuration file is located in
   ``/etc/sahara/sahara.conf``. For details see
   :doc:`Sahara Configuration Guide <../admin/configuration-guide>`

4. Create the database schema:

.. sourcecode:: console

    # sahara-db-manage --config-file /etc/sahara/sahara.conf upgrade head
..

5. Go through :ref:`common_installation_steps` and make any
   necessary changes.

6. Start the sahara-api and sahara-engine services:

.. sourcecode:: console

    # systemctl start openstack-sahara-api
    # systemctl start openstack-sahara-engine
..

7. *(Optional)* Enable sahara services to start on boot

.. sourcecode:: console

    # systemctl enable openstack-sahara-api
    # systemctl enable openstack-sahara-engine
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

2. Setup a virtual environment for sahara:

.. sourcecode:: console

    $ virtualenv sahara-venv
..

This will install a python virtual environment into ``sahara-venv``
directory in your current working directory. This command does not
require super user privileges and can be executed in any directory where
the current user has write permissions.

3. You can get a sahara archive from
   `<http://tarballs.openstack.org/sahara/>`_ and install it using pip:

.. sourcecode:: console

    $ sahara-venv/bin/pip install 'http://tarballs.openstack.org/sahara/sahara-master.tar.gz'
..

Note that ``sahara-master.tar.gz`` contains the latest changes and
might not be stable at the moment. We recommend browsing
`<http://tarballs.openstack.org/sahara/>`_ and selecting the latest
stable release. For installation just execute (where replace the 'release'
word with release name, e.g. 'mitaka'):

.. sourcecode:: console

    $ sahara-venv/bin/pip install 'http://tarballs.openstack.org/sahara/sahara-stable-release.tar.gz'
..

For example, you can get Sahara Mitaka release by executing:

.. sourcecode:: console

    $ sahara-venv/bin/pip install 'http://tarballs.openstack.org/sahara/sahara-stable-mitaka.tar.gz'
..

4. After installation you should create a configuration file; as seen below it
   is possible to generate a sample one:

.. sourcecode:: console

    $ SAHARA_SOURCE_DIR="/path/to/sahara/source"
    $ pushd $SAHARA_SOURCE_DIR
    $ tox -e genconfig
    $ popd
    $ cp $SAHARA_SOURCE_DIR/etc/sahara/sahara.conf.sample sahara-venv/etc/sahara.conf
..

Make any necessary changes to ``sahara-venv/etc/sahara.conf``.
For details see
:doc:`Sahara Configuration Guide <../admin/configuration-guide>`

.. _common_installation_steps:

Common installation steps
-------------------------

The steps below are common to both the RDO and virtual environment
installations of sahara.

1. If you use sahara with a MySQL database, then for storing big job binaries
   in the sahara internal database you must configure the size of the maximum
   allowed packet. Edit the ``my.cnf`` file and change the
   ``max_allowed_packet`` parameter as follows:

.. sourcecode:: ini

   ...
   [mysqld]
   ...
   max_allowed_packet = 256M
..

Then restart the mysql server to ensure these changes are active.

2. Create the database schema:

.. sourcecode:: console

    $ sahara-venv/bin/sahara-db-manage --config-file sahara-venv/etc/sahara.conf upgrade head
..

3. Start sahara services from different terminals:

.. sourcecode:: console

    # first terminal
    $ sahara-venv/bin/sahara-api --config-file sahara-venv/etc/sahara.conf

    # second terminal
    $ sahara-venv/bin/sahara-engine --config-file sahara-venv/etc/sahara.conf
..

.. _register-sahara-label:

4. For sahara to be accessible in the OpenStack Dashboard and for
   python-saharaclient to work properly you must register sahara in
   the Identity service catalog. For example:

.. code-block::

    $ openstack service create --name sahara --description \
      "Sahara Data Processing" data-processing

    $ openstack endpoint create --region RegionOne \
      data-processing public http://10.0.0.2:8386/v1.1/%\(project_id\)s

    $ openstack endpoint create --region RegionOne \
      data-processing internal http://10.0.0.2:8386/v1.1/%\(project_id\)s

    $ openstack endpoint create --region RegionOne \
      data-processing admin http://10.0.0.2:8386/v1.1/%\(project_id\)s

.. note::

   You have to install the openstack-client package in order to execute
   ``openstack`` command.
..

5. For more information on configuring sahara with the OpenStack Dashboard
   please see :doc:`dashboard-guide`.

Optional installation of default templates
------------------------------------------

Sahara bundles default templates that define simple clusters for the
supported plugins. These templates may optionally be added to the
sahara database using a simple CLI included with sahara.

The default template CLI is described in detail in a *README* file
included with the sahara sources at ``<sahara_home>/db/templates/README.rst``
but it is summarized here.

Flavor id values must be specified for the default templates included
with sahara. The recommended configuration values below correspond to the
*m1.medium* and *m1.large* flavors in a default OpenStack installation (if
these flavors have been edited, their corresponding values will be different).
Values for flavor_id should be added to ``/etc/sahara/sahara.conf`` or another
configuration file in the sections shown here:

.. sourcecode:: ini

    [DEFAULT]
    # Use m1.medium for {flavor_id} unless specified in another section
    flavor_id = 2

    [cdh-5-default-namenode]
    # Use m1.large for {flavor_id} in the cdh-5-default-namenode template
    flavor_id = 4

    [cdh-530-default-namenode]
    # Use m1.large for {flavor_id} in the cdh-530-default-namenode template
    flavor_id = 4

The above configuration values are included in a sample configuration
file at ``<sahara_home>/plugins/default_templates/template.conf``

The command to install all of the default templates is as follows, where
``$PROJECT_ID`` should be a valid project id and the above configuration values
have been set in ``myconfig``:

.. sourcecode:: console

    $ sahara-templates --config-file /etc/sahara/sahara.conf --config-file myconfig update -t $PROJECT_ID

Help is available from the ``sahara-templates`` command:

.. sourcecode:: console

    $ sahara-templates --help
    $ sahara-templates update --help

Notes:
------

Ensure that your operating system is not blocking the sahara port
(default: 8386). You may need to configure iptables in CentOS and
other Linux distributions to allow this access.

To get the list of all possible options run:

.. sourcecode:: console

    $ sahara-venv/bin/python sahara-venv/bin/sahara-api --help
    $ sahara-venv/bin/python sahara-venv/bin/sahara-engine --help
..

Further, consider reading :doc:`../intro/overview` for general sahara
concepts and :doc:`../user/plugins` for specific plugin
features/requirements.
