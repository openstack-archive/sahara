Setting Up a Development Environment
====================================

This page describes how to point a local running Savanna instance to a Devstack deployed in a VM.
You should be able to debug and test your changes without having to deploy.

Setup VM with DevStack
----------------------

.. toctree::
    :maxdepth: 1

    devstack


Setup Local Environment
-----------------------

Now we are going to setup development environment for Savanna on your OS.

1. Install prerequisites

On OS X Systems:

.. sourcecode:: console

    # we actually need pip, which is part of python package
    $ brew install python
    $ pip install virtualenv tox

On Ubuntu:

.. sourcecode:: console

    $ sudo apt-get install git-core python-dev python-virtualenv
    $ sudo pip install tox

On Fedora-based distributions (e.g., Fedora/RHEL/CentOS/Scientific Linux):

.. sourcecode:: console

    $ sudo yum install git-core python-devel python-virtualenv
    $ sudo pip install tox

2. Grab the code from GitHub:

.. sourcecode:: console

    $ git clone git://github.com/stackforge/savanna.git
    $ cd savanna

3. Prepare virtual environment:

.. sourcecode:: console

    $ tools/install_venv

4. Create config file from default template:

.. sourcecode:: console

    $ cp ./etc/savanna/savanna.conf.sample ./etc/savanna/savanna.conf

5. Look through the savanna.conf and change parameters which default values do not suite you.
Set ``os_auth_host`` to the address of your VM with DevStack.

.. note::

    Config file can be specified for ``savanna-api`` command using ``--config-file`` flag.

6. To start Savanna call:

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

