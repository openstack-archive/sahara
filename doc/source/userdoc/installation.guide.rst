Savanna Installation Guide
==========================

We recommend installing Savanna into virtual environment. That guaranties that if you already
have some python packages installed ith OS package manager, Savanna installation will not
mess with them. Still, installing Savanna into system makes sense if that system is dedicated to
Savanna.

Further steps describe Savanna installation into virtual environment. All steps except
#1 do not require superuser privileges.


1. First you need to install `python-setuptools`, `python-virtualenv` and python headers using your
   OS package manager. The python headers package name depends on OS. For Ubuntu it is `python-dev`,
   for Red Hat - `python-devel` So for Ubuntu run :

.. sourcecode:: console

    $ sudo apt-get install python-setuptools python-virtualenv python-dev
..

   For Red Hat:

.. sourcecode:: console

    $ sudo yum install python-setuptools python-virtualenv python-devel

2. Setup virtual environment for Savanna:

.. sourcecode:: console

    $ virtualenv savanna-venv

3. You can install the latest Savanna release version from pypi:

.. sourcecode:: console

    $ savanna-venv/bin/pip install savanna
..

   Or you can get Savanna archive from `<http://tarballs.openstack.org/savanna/>`_ and install it using pip:

.. sourcecode:: console

    $ savanna-venv/bin/pip install 'http://tarballs.openstack.org/savanna/savanna-master.tar.gz#egg=savanna'
..

   Note that savanna-master contains the latest changes and might not be stable at the moment.
   We recommend browsing `<http://tarballs.openstack.org/savanna/>`_ and selecting the latest stable release.

4. After installation you should create configuration file. Sample config file location
   depends on your OS. For Ubuntu it is ``/usr/local/share/savanna/savanna.conf.sample``,
   for Red Hat - ``/usr/share/savanna/savanna.conf.sample``. Below is an example for Ubuntu:

.. sourcecode:: console

    $ mkdir savanna-venv/etc
    $ cp savanna-venv/share/savanna/savanna.conf.sample savanna-venv/etc/savanna.conf

5. To start Savanna call:

.. sourcecode:: console

    $ savanna-venv/bin/python savanna-venv/bin/savanna-api --config-file savanna-venv/etc/savanna.conf
..

   To get the list of all possible options run:

.. sourcecode:: console

    $ savanna-venv/bin/python savanna-venv/bin/savanna-api --help
