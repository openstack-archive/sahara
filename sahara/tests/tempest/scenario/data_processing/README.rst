Tests for Sahara Client in Tempest
====================================

How to run
----------

Get the latest tempest resources from GitHub:

.. sourcecode:: console

    $ git clone https://github.com/openstack/tempest.git
..

Create a configuration file ``tempest/etc/tempest.conf`` for tempest using the sample file
from ``tempest/etc/tempest.conf.sample``:

.. sourcecode:: console

    $ cd $TEMPEST_ROOT_DIR
    $ cp etc/tempest.conf.sample etc/tempest.conf
..

Some configuration options are required for running tests. Here is the list:

[DEFAULT]
lock_path=

[identity]
uri=
uri_v3=
username=
tenant_name=
password=
admin_username=
admin_tenant_name=
admin_password=

[service_available]
sahara=true
neutron=true

Get the latest sahara resources from GitHub:

.. sourcecode:: console

    $ git clone https://github.com/openstack/sahara.git
..

Copy Sahara Tempest tests directory to tempest:

.. sourcecode:: console

    $ cp -r $SAHARA_ROOT_DIR/sahara/tests/tempest .
..

Create a configuration file ``tempest/scenario/data_processing/etc/sahara_tests.conf`` from
``tempest/scenario/data_processing/etc/sahara_tests.conf.sample``:

.. sourcecode:: console

    $ cp tempest/scenario/data_processing/etc/sahara_tests.conf.sample tempest/scenario/data_processing/etc/sahara_tests.conf
..

All options should be set. Some of them are defaults and can be left without changing,
other should be specified.

When configuration is finished, you can launch the tests with:

.. sourcecode:: console

    $ tox -e all -- tempest.scenario.data_processing.client_tests
..

If you want to launch all Sahara tests in Tempest, you can do this with ``data_processing`` tag:

.. sourcecode:: console

    $ tox -e all -- data_processing
..