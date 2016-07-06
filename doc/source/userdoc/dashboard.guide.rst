OpenStack Dashboard Configuration Guide
=======================================

Sahara UI panels are integrated into the OpenStack Dashboard repository. No
additional steps are required to enable Sahara UI in OpenStack Dashboard.
However there are a few configurations that should be made to configure
OpenStack Dashboard.

Dashboard configurations are applied through the local_settings.py file.
The sample configuration file is available `here. <https://github.com/openstack/horizon/blob/master/openstack_dashboard/local/local_settings.py.example>`_

1. Networking
-------------

Depending on the Networking backend (Nova Network or Neutron) used in the
cloud, Sahara panels will determine automatically which input fields should be
displayed.

While using Nova Network backend the cloud may be configured to automatically
assign floating IPs to instances. If Sahara service is configured to use those
automatically assigned floating IPs the same configuration should be done to
the dashboard through the ``SAHARA_AUTO_IP_ALLOCATION_ENABLED`` parameter.

Example:

.. sourcecode:: python

    SAHARA_AUTO_IP_ALLOCATION_ENABLED = True
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

.. sourcecode:: console

    openstack service create --name sahara_local --description \
        "Sahara Data Processing (local installation)" \
        data_processing_local

    openstack endpoint create --region RegionOne \
    --publicurl http://127.0.0.1:8386/v1.1/%\(tenant_id\)s \
    --adminurl http://127.0.0.1:8386/v1.1/%\(tenant_id\)s \
    --internalurl http://127.0.0.1:8386/v1.1/%\(tenant_id\)s \
    data_processing_local
..

Then the endpoint name should be changed in ``sahara.py`` under the module of
`sahara-dashboard/sahara_dashboard/api/sahara.py. <https://github.com/openstack/sahara-dashboard/blob/master/sahara_dashboard/api/sahara.py>`_

.. sourcecode:: python

    # "type" of Sahara service registered in keystone
    SAHARA_SERVICE = 'data_processing_local'
