Savanna Horizon Setup
=====================

1 Setup prerequisites
---------------------

1.1 OpenStack environment (Folsom+ version) installed.

1.2 Savanna REST API service installed and configured.

1.3 Operating system, where Savanna Horizon’s service installed, has to be connected to internal OpenStack network.

2 Savanna-Horizon Installation
------------------------------

2.1 Go to your Horizon’s machine and install the following packets:

.. sourcecode:: bash

    sudo apt-get update
    sudo apt-get install git python-dev gcc python-setuptools python-virtualenv node-less

On Ubuntu 12.10 and higer you have to install the following lib as well:

.. sourcecode:: bash

    sudo apt-get install nodejs-legacy

2.2 Clone Horizon’s Git repo:

.. sourcecode:: bash

    git clone -b savanna https://github.com/Mirantis/openstack-horizon.git

**Note:** Above link will be changed soon when project moved to StackForge.

2.3 Create the following structure of directories:

.. sourcecode:: bash

    sudo mkdir -p <path_to_horizon>/bin/less
    sudo ln -s /usr/bin/lessc <path_to_horizon>/bin/less/lessc

2.4 Go to cloned directory:

.. sourcecode:: bash

    cd <path_to_horizon>

2.5 Install Python virtual environment:

.. sourcecode:: bash

    python tools/install_venv.py

This operation will install **.venv** in the current directory

2.6 Create configuration file:

.. sourcecode:: bash

    cp openstack_dashboard/local/local_settings.py.example openstack_dashboard/local/local_settings.py

2.7 Change **openstack_dashboard/local/local_settings.py** file with the following parameters:

2.7.1 Set **OPENSTACK_HOST** to KeyStone URL:

Here is a snippet of code with the changed parameter:

.. sourcecode:: python

    [skipped]

    OPENSTACK_HOST = "172.18.79.139"    <------ KeyStone address
    OPENSTACK_KEYSTONE_URL = "http://%s:5000/v2.0" % OPENSTACK_HOST
    OPENSTACK_KEYSTONE_DEFAULT_ROLE = "Member"

    [skipped]

2.8 Change **openstack_dashboard/wsgi/django.wsgi** file to make virtualenv packages available for apache

Here are the required modifications

.. sourcecode:: python
    
    import logging
    import os
    import sys

    venv_path = "<path_to_horizon>/.venv/"    <---------- Horizon .venv directory
    activate_this = os.path.join(venv_path, "bin/activate_this.py")
    execfile(activate_this, dict(__file__=activate_this))

    from django.conf import settings
    import django.core.handlers.wsgi

    [skipped]


3 Configure apache2 server
--------------------------

3.1 Install apache and mod_wsgi

.. sourcecode:: bash

   sudo apt-get install apache2 libapache2-mod-wsgi

3.2 Create **/etc/apache2/sites-available/horizon** file

Here is the apache configuration

.. sourcecode:: bash
   
    <VirtualHost *:80>
   	WSGIScriptAlias / <horizon-path>/openstack_dashboard/wsgi/django.wsgi
	WSGIDaemonProcess horizon user=<user> group=<group> processes=3 threads=10 home=<horizon-path> python-path=<horizon-path>:<horizon-path>/.venv/lib/python-2.7/site-packages
	WSGIApplicationGroup %{GLOBAL}

        SetEnv APACHE_RUN_USER <user>
        SetEnv APACHE_RUN_GROUP <user>
        WSGIProcessGroup horizon

        DocumentRoot <horizon-path>/.blackhole/
        Alias /media <horizon-path>/openstack_dashboard/static

        <Directory />
            Options FollowSymLinks
            AllowOverride None
        </Directory>

        <Directory <horizon-path>/>
            Options Indexes FollowSymLinks MultiViews
            AllowOverride None
            Order allow,deny
            allow from all
        </Directory>

        ErrorLog /var/log/apache2/horizon_error.log
        LogLevel warn
        CustomLog /var/log/apache2/horizon_access.log combined
    </VirtualHost>

    WSGISocketPrefix /var/run/apache2

Replace following parameters:

- <user> - username
- <group> - group
- <horizon-path> - path to horizon directory

3.3 Enable horizon site

.. sourcecode:: bash
    
   sudo a2ensite horizon


Now all installations are done and Horizon can be started:

.. sourcecode:: bash

    sudo service apache2 restart


You can check that service has been started successfully. Go to Horizon URL and you'll be able to see Savanna pages in the Project tab.
