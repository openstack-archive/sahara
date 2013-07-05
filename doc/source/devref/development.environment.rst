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

.. sourcecode:: bash

	# we actually need pip, which is part of python package
	brew install python
	pip install virtualenv tox

On Ubuntu:

.. sourcecode:: bash

	sudo apt-get install python-dev python-virtualenv
	sydo pip install tox

On Fedora-based distributions (e.g., Fedora/RHEL/CentOS/Scientific Linux):

.. sourcecode:: bash

	sudo yum install python-devel python-virtualenv
	sudo pip install tox

2. Grab the code from GitHub:

.. sourcecode:: bash

    git clone git://github.com/stackforge/savanna.git
    cd savanna

3. Prepare virtual environment:

.. sourcecode:: bash

    tools/install_venv

4. Create config file from default template:

.. sourcecode:: bash

    cp ./etc/savanna/savanna.conf.sample ./etc/savanna/savanna.conf

5. Look through the savanna.conf and change parameters which default values do not suite you.
Set ``os_auth_host`` to the address of your VM with DevStack.

.. note::

	Config file can be specified for ``savanna-api`` command using ``--config-file`` flag.

6. To start Savanna call:

.. sourcecode:: bash

    tox -evenv -- savanna-api --config-file etc/savanna/savanna.conf --allow-cluster-ops


Setup local OpenStack dashboard with Savanna plugin
---------------------------------------------------

.. toctree::
    :maxdepth: 1


    ../horizon/dev.environment.guide