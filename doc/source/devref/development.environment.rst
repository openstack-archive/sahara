Setting Up a Development Environment
====================================

This page describes how to point a local running Savanna instance to a Devstack deployed in a VM.
You should be able to debug and test your changes without having to deploy.


Setup VM for DevStack
---------------------

In order to run Devstsack in a local VM, you need to start by installing a guest with Ubuntu 12.04 server.
Download an image file from `Ubuntu's web site <http://www.ubuntu.com/download/server>`_ and create a new guest from it.
Virtualization solution should support nested virtualization.

**On Mac OS X Systems**

Install VMWare Fusion and create a new VM with Ubuntu Server 12.04.
Recommended settings:

- Processor - at least 2 cores
- Enable hypervisor applications in this virtual machine
- Memory - at least 4GB
- Hard Drive - at least 60GB


**On Linux Systems**

Use KVM

TBD: add more details.



Install DevStack on VM
----------------------

Now we are going to install DevStack in VM we just created. So, connect to VM with secure shell and follow instructions.

1. Clone DevStack:

.. sourcecode:: bash

	sudo apt-get install git-core
	git clone https://github.com/openstack-dev/devstack.git

2. Create file localrc in devstack directory with the following content:

.. sourcecode:: bash

	ADMIN_PASSWORD=nova
	MYSQL_PASSWORD=nova
	RABBIT_PASSWORD=nova
	SERVICE_PASSWORD=$ADMIN_PASSWORD
	SERVICE_TOKEN=nova

	# keystone is now configured by default to use PKI as the token format which produces huge tokens.
	# set UUID as keystone token format which is much shorter and easier to work with.
	KEYSTONE_TOKEN_FORMAT=UUID

	# Change the FLOATING_RANGE to whatever IPs VM is working in.
	# In NAT mode it is subnet VMWare Fusion provides, in bridged mode it is your local network.
	# But only use the top end of the network by using a /27 and starting at the 224 octet.
	FLOATING_RANGE=172.16.94.224/27

	# Enable auto assignment of floating IPs. By default Savanna expects this setting to be enabled
	EXTRA_OPTS=(auto_assign_floating_ip=True)

3. Start DevStack:

.. sourcecode:: bash

	./stack.sh

4. Once previous step is finished Devstack will print Horizon URL.
Navigate to this URL and login with login "admin" and password from localrc.

5. Now we need to modify security rules. It will allow to connect to VMs directly from your host.
Navigate to project's "Admin" security tab and edit default Security Group rules:

	TCP, Port range 1-65535, CIDR, 0.0.0.0/0
	ICMP, -1, -1, CIDR, 0.0.0.0/0

6. Congratulations! You have OpenStack running in your VM and ready to launch VMs inside that VM :)


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

.. note::

	Config file can be specified for ``savanna-api`` and ``savanna-manage`` commands using ``--config-file`` flag.

6. To initialize Savanna database with predefined configs and templates just call:

.. sourcecode:: bash

    tox -evenv -- savanna-manage --config-file etc/savanna/savanna.conf reset-db --with-gen-templates

Virtualenv with all requirements is now installed into ``.tox/venv``.

7. To start Savanna call:

.. sourcecode:: bash

    tox -evenv -- savanna-api --config-file etc/savanna/savanna.conf --allow-cluster-ops

