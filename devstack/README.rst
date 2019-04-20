======================
 Enabling in Devstack
======================

1. Download DevStack

2. Add this repo as an external repository in ``local.conf``

.. sourcecode:: bash

     [[local|localrc]]
     enable_plugin sahara https://opendev.org/openstack/sahara
     enable_plugin heat https://opendev.org/openstack/heat

Optionally, a git refspec may be provided as follows:

.. sourcecode:: bash

     [[local|localrc]]
     enable_plugin sahara https://opendev.org/openstack/sahara <refspec>

3. run ``stack.sh``
