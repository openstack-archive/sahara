Setting Up a Development Environment
====================================

This page describes how to setup a Sahara development environment by either
installing it as a part of DevStack or pointing a local running instance at an
external OpenStack. You should be able to debug and test your changes without
having to deploy Sahara.

Setup a Local Environment with Sahara inside DevStack
-----------------------------------------------------

See :doc:`the main article <devstack>`.

Setup a Local Environment with an external OpenStack
----------------------------------------------------

1. Install prerequisites

On OS X Systems:

.. sourcecode:: console

    # we actually need pip, which is part of python package
    $ brew install python mysql postgresql rabbitmq
    $ pip install virtualenv tox

On Ubuntu:

.. sourcecode:: console

    $ sudo apt-get update
    $ sudo apt-get install git-core python-dev python-virtualenv gcc libpq-dev libmysqlclient-dev python-pip rabbitmq-server
    $ sudo pip install tox

On Red Hat and related distributions (CentOS/Fedora/RHEL/Scientific Linux):

.. sourcecode:: console

    $ sudo yum install git-core python-devel python-virtualenv gcc python-pip mariadb-devel postgresql-devel erlang
    $ sudo pip install tox
    $ sudo wget http://www.rabbitmq.com/releases/rabbitmq-server/v3.2.2/rabbitmq-server-3.2.2-1.noarch.rpm
    $ sudo rpm --import http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
    $ sudo yum install rabbitmq-server-3.2.2-1.noarch.rpm

On openSUSE-based distributions (SLES 12, openSUSE, Factory or Tumbleweed):

.. sourcecode:: console

    $ sudo zypper in gcc git libmysqlclient-devel postgresql-devel python-devel python-pip python-tox python-virtualenv

2. Grab the code

.. sourcecode:: console

    $ git clone https://opendev.org/openstack/sahara.git
    $ cd sahara

3. Generate Sahara sample using tox

.. sourcecode:: console

   tox -e genconfig

4. Create config file from the sample

.. sourcecode:: console

    $ cp ./etc/sahara/sahara.conf.sample ./etc/sahara/sahara.conf

5. Look through the sahara.conf and modify parameter values as needed
   For details see
   :doc:`Sahara Configuration Guide <../admin/configuration-guide>`

6. Create database schema

.. sourcecode:: console

    $ tox -e venv -- sahara-db-manage --config-file etc/sahara/sahara.conf upgrade head

7. To start Sahara API and Engine processes call

.. sourcecode:: console

    $ tox -e venv -- sahara-api --config-file etc/sahara/sahara.conf --debug
    $ tox -e venv -- sahara-engine --config-file etc/sahara/sahara.conf --debug


Setup local OpenStack dashboard with Sahara plugin
--------------------------------------------------

.. toctree::
    :maxdepth: 1


    dashboard-dev-environment-guide

Tips and tricks for dev environment
-----------------------------------

1. Pip speedup

Add the following lines to ~/.pip/pip.conf

.. sourcecode:: cfg

    [global]
    download-cache = /home/<username>/.pip/cache
    index-url = <mirror url>

Note that the ``~/.pip/cache`` folder should be created manually.

2. Git hook for fast checks

Just add the following lines to .git/hooks/pre-commit and do chmod +x for it.

.. sourcecode:: console

    #!/bin/sh
    # Run fast checks (PEP8 style check and PyFlakes fast static analysis)
    tox -epep8

You can add also other checks for pre-push, for example pylint (see below)
and tests (tox -epy27).

3. Running static analysis (PyLint)

Just run the following command

.. sourcecode:: console

    tox -e pylint
