Savanna Installation Guide
==========================

1. You can install the latest Savanna release version from pypi:

.. sourcecode:: bash

    sudo pip install savanna

Or you can get Savanna archive from http://tarballs.openstack.org/savanna/ and install it using pip:

.. sourcecode:: bash

    sudo pip install http://tarballs.openstack.org/savanna/savanna-master.tar.gz#egg=savanna

.. note::

    savanna-master.tar.gz contains the latest changes in the source code.
    savanna-some_version.tar.gz contains features related to specified Savanna release.


2. After installation you should create configuration file or change default config to run Savanna properly. Default config file is located in:

.. sourcecode:: bash

    sudo mkdir /etc/savanna
    sudo cp /usr/local/share/savanna/savanna.conf.sample /etc/savanna/savanna.conf

3. To initialize Savanna database with created configuration just call:

.. sourcecode:: bash

    savanna-manage --config-file /etc/savanna/savanna.conf reset-db --with-gen-templates

4. To start Savanna call:

.. sourcecode:: bash

    savanna-api --config-file /etc/savanna/savanna.conf