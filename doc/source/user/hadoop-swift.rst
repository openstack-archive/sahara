.. _swift-integration-label:

Swift Integration
=================
Hadoop and Swift integration are the essential continuation of the
Hadoop/OpenStack marriage. The key component to making this marriage work is
the Hadoop Swift filesystem implementation. Although this implementation has
been merged into the upstream Hadoop project, Sahara maintains a version with
the most current features enabled.

* The original Hadoop patch can be found at
  https://issues.apache.org/jira/browse/HADOOP-8545

* The most current Sahara maintained version of this patch can be found in the
  `Sahara Extra repository <https://opendev.org/openstack/sahara-extra>`_

* The latest compiled version of the jar for this component can be downloaded
  from https://tarballs.openstack.org/sahara-extra/dist/hadoop-openstack/master/

Now the latest version of this jar (which uses Keystone API v3) is used in
the plugins' images automatically during build of these images. But for
Ambari plugin we need to explicitly put this jar into /opt directory of the
base image **before** cluster launching.

Hadoop patching
---------------
You may build the jar file yourself by choosing the latest patch from the
Sahara Extra repository and using Maven to build with the pom.xml file
provided. Or you may get the latest jar pre-built at
https://tarballs.openstack.org/sahara-extra/dist/hadoop-openstack/master/

You will need to put this file into the hadoop libraries
(e.g. /usr/lib/share/hadoop/lib, it depends on the plugin which you use) on
each ResourceManager and NodeManager node (for Hadoop 2.x) in the cluster.

Hadoop configurations
---------------------
In general, when Sahara runs a job on a cluster it will handle configuring the
Hadoop installation. In cases where a user might require more in-depth
configuration all the data is set in the ``core-site.xml`` file on the cluster
instances using this template:

.. code-block::

    <property>
        <name>${name} + ${config}</name>
        <value>${value}</value>
        <description>${not mandatory description}</description>
    </property>


There are two types of configs here:

1. General. The ``${name}`` in this case equals to ``fs.swift``. Here is the
   list of ``${config}``:

   * ``.impl`` - Swift FileSystem implementation. The ${value} is
     ``org.apache.hadoop.fs.swift.snative.SwiftNativeFileSystem``
   * ``.connect.timeout`` - timeout for all connections by default: 15000
   * ``.socket.timeout`` - how long the connection waits for responses from
     servers. by default: 60000
   * ``.connect.retry.count`` - connection retry count for all connections. by
     default: 3
   * ``.connect.throttle.delay`` - delay in millis between bulk (delete,
     rename, copy operations). by default: 0
   * ``.blocksize`` - blocksize for filesystem. By default: 32Mb
   * ``.partsize`` - the partition size for uploads. By default: 4608*1024Kb
   * ``.requestsize`` - request size for reads in KB. By default: 64Kb


2. Provider-specific. The patch for Hadoop supports different cloud providers.
   The ``${name}`` in this case equals to ``fs.swift.service.${provider}``.

   Here is the list of ``${config}``:

   * ``.auth.url`` - authorization URL
   * ``.auth.endpoint.prefix`` - prefix for the service url, e.g. ``/AUTH_``
   * ``.tenant`` - project name
   * ``.username``
   * ``.password``
   * ``.domain.name`` - Domains can be used to specify users who are not in
     the project specified.
   * ``.domain.id`` - You can also specify domain using id.
   * ``.trust.id`` - Trusts are optionally  used to scope the authentication
     tokens of the supplied user.
   * ``.http.port``
   * ``.https.port``
   * ``.region`` - Swift region is used when cloud has more than one Swift
     installation. If region param is not set first region from Keystone
     endpoint list will be chosen. If region param not found exception will be
     thrown.
   * ``.location-aware`` - turn On location awareness. Is false by default
   * ``.apikey``
   * ``.public``


Example
-------
For this example it is assumed that you have setup a Hadoop instance with
a valid configuration and the Swift filesystem component. Furthermore there is
assumed to be a Swift container named ``integration`` holding an object named
``temp``, as well as a Keystone user named ``admin`` with a password of
``swordfish``.

The following example illustrates how to copy an object to a new location in
the same container. We will use Hadoop's ``distcp`` command
(http://hadoop.apache.org/docs/stable/hadoop-distcp/DistCp.html) to accomplish the copy.
Note that the service provider for our Swift access is ``sahara``, and that
we will not need to specify the project of our Swift container as it will
be provided in the Hadoop configuration.

Swift paths are expressed in Hadoop according to the following template:
``swift://${container}.${provider}/${object}``. For our example source this
will appear as ``swift://integration.sahara/temp``.

Let's run the job:

.. sourcecode:: console

    $ hadoop distcp -D fs.swift.service.sahara.username=admin \
     -D fs.swift.service.sahara.password=swordfish \
     swift://integration.sahara/temp swift://integration.sahara/temp1

After that just confirm that ``temp1`` has been created in our ``integration``
container.

Limitations
-----------

**Note:** Please note that container names should be a valid URI.
