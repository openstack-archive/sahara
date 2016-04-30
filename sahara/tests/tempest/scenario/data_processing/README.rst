Tests for Sahara Client in Tempest
====================================

How to run
----------

Get the latest sahara resources from the appropriate mirror:

.. sourcecode:: console

    $ git clone https://github.com/openstack/sahara.git
..

Install sahara, in order to register the tempest plugin interface:

.. sourcecode:: console

    $ pip install $SAHARA_ROOT_DIR
..

Get the latest python-saharaclient resources from the appropriate mirror:

.. sourcecode:: console

    $ git clone https://github.com/openstack/python-saharaclient.git
..

Install python-saharaclient:

.. sourcecode:: console

    $ pip install $SAHARACLIENT_ROOT_DIR
..

Get the latest tempest resources from the appropriate mirror:

.. sourcecode:: console

    $ git clone https://github.com/openstack/tempest.git
..

Create a configuration file ``tempest/etc/tempest.conf`` for tempest.
The sample file can be generated and used for this purpose:

.. sourcecode:: console

    $ cd $TEMPEST_ROOT_DIR
    $ tox -e genconfig
    $ cp etc/tempest.conf.sample etc/tempest.conf
..

Some configuration options are required for running tests. Here is the list:

.. sourcecode:: ini

    [auth]
    admin_username=
    admin_project_name=
    admin_password=

    [identity]
    uri=
    uri_v3=

    [compute]
    fixed_network_name=
    flavor_ref=

    [network]
    floating_network_name=
    public_network_id=

    [data-processing]
    fake_image_id=

    [validation]
    image_ssh_user=

    [service_available]
    sahara=true
    neutron=true

..

All the parameters above are defined by tempest, with the exception of
data_processing.fake_image_id, which is defined by the scenario python
client tests here.

Other relevant parameters (all defined by scenario python client tests):

.. sourcecode:: ini

    [data-processing]
    ...
    endpoint_type=
    catalog_type=
    saharaclient_version=1.1
    sahara_url=
    cluster_timeout=1800
    request_timeout=10

..

When configuration is finished, you can launch the tests from tempest with:

.. sourcecode:: console

    $ tox -e all-plugin -- tempest.scenario.data_processing.client_tests
..

If you want to launch all Sahara tests in Tempest, you can do this with ``data_processing`` tag:

.. sourcecode:: console

    $ tox -e all-plugin -- data_processing
..
