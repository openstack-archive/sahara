Sahara Dashboard Configuration Guide
====================================

After installing the Sahara dashboard, there are a few extra configurations
that can be made.

Dashboard configurations are applied through Horizon's local_settings.py file.
The sample configuration file is available `from the Horizon repository. <https://opendev.org/openstack/horizon/src/branch/master/openstack_dashboard/local/local_settings.py.example>`_

1. Networking
-------------

Depending on the Networking backend (Neutron) used in the
cloud, Sahara panels will determine automatically which input fields should be
displayed.

If you wish to disable floating IP options during node group template
creation, add the following parameter:

Example:

.. sourcecode:: python

    SAHARA_FLOATING_IP_DISABLED = True
..

2. Different endpoint
---------------------

Sahara UI panels normally use ``data-processing`` endpoint from Keystone to
talk to Sahara service. In some cases it may be useful to switch to another
endpoint, for example use locally installed Sahara instead of the one on the
OpenStack controller.

To switch the UI to another endpoint the endpoint should be registered in the
first place.

Local endpoint example:

.. code-block::

    $ openstack service create --name sahara_local --description \
      "Sahara Data Processing (local installation)" \
      data_processing_local

    $ openstack endpoint create --region RegionOne \
      data_processing_local public http://127.0.0.1:8386/v1.1/%\(project_id\)s

    $ openstack endpoint create --region RegionOne \
      data_processing_local internal  http://127.0.0.1:8386/v1.1/%\(project_id\)s

    $ openstack endpoint create --region RegionOne \
      data_processing_local admin http://127.0.0.1:8386/v1.1/%\(project_id\)s
..

Then the endpoint name should be changed in ``sahara.py`` under the module of
`sahara-dashboard/sahara_dashboard/api/sahara.py
<https://opendev.org/openstack/sahara-dashboard/src/branch/master/sahara_dashboard/api/sahara.py>`__.

.. sourcecode:: python

    # "type" of Sahara service registered in keystone
    SAHARA_SERVICE = 'data_processing_local'


3. Hiding health check info
---------------------------

Sahara UI panels normally contain some information about cluster health. If
the relevant functionality has been disabled in the Sahara service, then
operators may prefer to not have any references to health at all in the UI,
since there would not be any usable health information in that case.

The visibility of health check info can be toggled via the
``SAHARA_VERIFICATION_DISABLED`` parameter, whose default value is False,
meaning that the health check info will be visible.

Example:

.. sourcecode:: python

    SAHARA_VERIFICATION_DISABLED = True
..
