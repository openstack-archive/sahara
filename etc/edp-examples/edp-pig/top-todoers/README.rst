Top TODOers Pig job
===================

This script calculates top TODOers in input sources.

Example of usage
----------------

This pig script can process as many input files (sources) as you want.
Just put all input files in a directory in HDFS or container in Swift and
give the path of the HDFS directory (Swift object) as input DataSource for EDP.

Here are steps how to prepare input data:

1. Create dir 'input'

.. sourcecode:: console

    $ mkdir input

2. Get some sources from GitHub and put it to 'input' directory:

.. sourcecode:: console

    $ cd input
    $ git clone "https://github.com/openstack/swift.git"
    $ git clone "https://github.com/openstack/nova.git"
    $ git clone "https://github.com/openstack/glance.git"
    $ git clone "https://github.com/openstack/image-api.git"
    $ git clone "https://github.com/openstack/neutron.git"
    $ git clone "https://github.com/openstack/horizon.git"
    $ git clone "https://github.com/openstack/python-novaclient.git"
    $ git clone "https://github.com/openstack/python-keystoneclient.git"
    $ git clone "https://github.com/openstack/oslo-incubator.git"
    $ git clone "https://github.com/openstack/python-neutronclient.git"
    $ git clone "https://github.com/openstack/python-glanceclient.git"
    $ git clone "https://github.com/openstack/python-swiftclient.git"
    $ git clone "https://github.com/openstack/python-cinderclient.git"
    $ git clone "https://github.com/openstack/ceilometer.git"
    $ git clone "https://github.com/openstack/cinder.git"
    $ git clone "https://github.com/openstack/heat.git"
    $ git clone "https://github.com/openstack/python-heatclient.git"
    $ git clone "https://github.com/openstack/python-ceilometerclient.git"
    $ git clone "https://github.com/openstack/oslo.config.git"
    $ git clone "https://github.com/openstack/ironic.git"
    $ git clone "https://github.com/openstack/python-ironicclient.git"
    $ git clone "https://github.com/openstack/operations-guide.git"
    $ git clone "https://github.com/openstack/keystone.git"
    $ git clone "https://github.com/openstack/oslo.messaging.git"
    $ git clone "https://github.com/openstack/oslo.sphinx.git"
    $ git clone "https://github.com/openstack/oslo.version.git"
    $ git clone "https://github.com/openstack/sahara.git"
    $ git clone "https://github.com/openstack/python-saharaclient.git"
    $ git clone "https://github.com/openstack/openstack.git"
    $ cd ..

3. Create single file containing all sources:

.. sourcecode:: console

    tar -cf input.tar input/*

.. note::

    Pig can operate with raw files as well as with compressed data, so in this
    step you might want to create *.gz file with sources and it should work.

4. Upload input.tar to Swift or HDFS as input data source for EDP processing