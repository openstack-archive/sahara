*********************
Savanna Horizon Setup
*********************

1 Setup prerequisites
=====================

1.1 OpenStack environment (Folsom+ version) installed.

1.2 Savanna REST API service installed and configured. You can find :doc:`quickstart guide here <..\quickstart>`.

1.3 Operating system, where Savanna Horizon’s service installed, has to be connected to internal OpenStack network.

2 Savanna-Horizon Installation
==============================

2.1 Go to your Horizon’s machine and install the following packets:

.. sourcecode:: bash

    sudo apt-get update
    sudo apt-get install git python-dev python-virtualenv node-less

On Ubuntu 12.10 and higer you have to install the following lib as well:

.. sourcecode:: bash

    sudo apt-get install nodejs-legacy

2.2 Create the following structure of directories:

.. sourcecode:: bash

    sudo mkdir -p /opt/stack/horizon/bin/less
    sudo ln -s /usr/bin/lessc /opt/stack/horizon/bin/less/lessc

2.3 Clone Horizon’s Git repo:

.. sourcecode:: bash

    git clone -b savanna https://github.com/Mirantis/openstack-horizon.git

**Note:** Above link will be changed soon when project moved to StackForge.

2.4 Go to cloned directory:

.. sourcecode:: bash

    cd openstack-horizon

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

    OPENSTACK_HOST = "172.18.79.139"    <------ your KeyStone URL
    OPENSTACK_KEYSTONE_URL = "http://%s:5000/v2.0" % OPENSTACK_HOST
    OPENSTACK_KEYSTONE_DEFAULT_ROLE = "Member"

    [skipped]

2.7.2 Set the custom **SECRET_KEY** by uncommenting the following two lines in **local_settings.py**:

.. sourcecode:: python

    from horizon.utils import secret_key
    SECRET_KEY = secret_key.generate_or_read_from_file(os.path.join(LOCAL_PATH, '.secret_key_store'))

Now all installations are ready and your Horizon service can be started:

.. sourcecode:: bash

    sudo tools/with_venv.sh ./manage.py runserver 0.0.0.0:80

You can check that service has been started successfully. Go to Horizon URL and you'll be able to see :doc:`Savanna pages <\index>` in the Project tab.
