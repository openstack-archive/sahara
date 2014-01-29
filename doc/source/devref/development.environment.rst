Setting Up a Development Environment
====================================

This page describes how to point a local running Savanna instance to remote OpenStack.
You should be able to debug and test your changes without having to deploy.

Setup Local Environment with Savanna inside DevStack
----------------------------------------------------

The easiest way to have local Savanna environment with DevStack is to include
Savanna component in DevStack.

.. toctree::
    :maxdepth: 1

    devstack

After you install DevStack with Savanna included you can rejoin screen with
``rejoin-stack.sh`` command and switch to ``savanna`` tab. Here you can manage
savanna service as other OpenStack services. Savanna source code is located at
``$DEST/savanna`` which is usually ``/opt/stack/savanna``.

Setup Local Environment with external OpenStack
-----------------------------------------------

1. Install prerequisites

On OS X Systems:

.. sourcecode:: console

    # we actually need pip, which is part of python package
    $ brew install python mysql postgresql
    $ pip install virtualenv tox

On Ubuntu:

.. sourcecode:: console

    $ sudo apt-get update
    $ sudo apt-get install git-core python-dev python-virtualenv gcc libpq-dev libmysqlclient-dev
    $ sudo pip install tox

On Fedora-based distributions (e.g., Fedora/RHEL/CentOS/Scientific Linux):

.. sourcecode:: console

    $ sudo yum install git-core python-devel python-virtualenv gcc python-pip mariadb-devel postgresql-devel
    $ sudo pip install tox

2. Grab the code from GitHub:

.. sourcecode:: console

    $ git clone git://github.com/openstack/savanna.git
    $ cd savanna

3. Prepare virtual environment:

.. sourcecode:: console

    $ tools/install_venv

4. Create config file from default template:

.. sourcecode:: console

    $ cp ./etc/savanna/savanna.conf.sample ./etc/savanna/savanna.conf

5. Look through the savanna.conf and change parameters which default values do
not suite you. Set ``os_auth_host`` to the address of OpenStack keystone.

If you are using Neutron instead of Nova Network add ``use_neutron = True`` to
config.  If the linux kernel you're utilizing support network namespaces then
also specify ``use_namespaces = True``.

.. note::

    Config file can be specified for ``savanna-api`` command using ``--config-file`` flag.

6. Create database schema:

.. sourcecode:: console

    $ tox -evenv -- savanna-db-manage --config-file etc/savanna/savanna.conf upgrade head

7. To start Savanna call:

.. sourcecode:: console

    $ tox -evenv -- savanna-api --config-file etc/savanna/savanna.conf -d


Setup local OpenStack dashboard with Savanna plugin
---------------------------------------------------

.. toctree::
    :maxdepth: 1


    ../horizon/dev.environment.guide

Tips and tricks for dev environment
-----------------------------------

1. Pip speedup

Add the following lines to ~/.pip/pip.conf

.. sourcecode:: cfg

    [global]
    download-cache = /home/<username>/.pip/cache
    index-url = <mirror url>

Note! The ``~/.pip/cache`` folder should be created.

2. Git hook for fast checks

Just add the following lines to .git/hooks/pre-commit and do chmod +x for it.

.. sourcecode:: console

    #!/bin/sh
    # Run fast checks (PEP8 style check and PyFlakes fast static analysis)
    tools/run_fast_checks

You can added the same check for pre-push, for example, run_tests and run_pylint.

3. Running static analysis (PyLint)

Just run the following command

.. sourcecode:: console

    tools/run_pylint

