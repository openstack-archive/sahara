Quickstart guide
================

This guide will help you setup a vanilla Hadoop cluster using a combination
of OpenStack command line tools and the sahara :doc:`REST API <../restapi>`.

1. Install sahara
-----------------

* If you want to hack the code follow
  :doc:`development.environment`.

OR

* If you just want to install and use sahara follow
  :doc:`../userdoc/installation.guide`.

2. Identity service configuration
---------------------------------

To use the OpenStack command line tools you should specify
environment variables with the configuration details for your OpenStack
installation. The following example assumes that the Identity service is
at ``127.0.0.1:5000``, with a user ``admin`` in the ``admin`` tenant
whose password is ``nova``:

.. sourcecode:: console

    $ export OS_AUTH_URL=http://127.0.0.1:5000/v2.0/
    $ export OS_TENANT_NAME=admin
    $ export OS_USERNAME=admin
    $ export OS_PASSWORD=nova

With these environment variables set you can get an authentication
token using the ``keystone`` command line client as follows:

.. sourcecode:: console

    $ keystone token-get

If authentication succeeds, the output will be as follows:

.. sourcecode:: console

    +-----------+----------------------------------+
    |  Property |              Value               |
    +-----------+----------------------------------+
    |  expires  |       2015-09-03T13:37:32Z       |
    |     id    | 2542c427092a4b09a07ee7612c3d99ae |
    | tenant_id | c82e4bce56ce4cf9b90bd15dfdef699d |
    |  user_id  | 7f5becaaa38b4c9e850ccd11672a4c96 |
    +-----------+----------------------------------+

The ``id`` and ``tenant_id`` values will be used for creating REST calls
to sahara and should be saved. The ``id`` value is the token provided by
the Identity service, and the ``tenant_id`` is the UUID for the tenant
name specified earlier. These values should be exported to environment
variables for ease of use later.

.. sourcecode:: console

    $ export AUTH_TOKEN="2542c427092a4b09a07ee7612c3d99ae"
    $ export TENANT_ID="c82e4bce56ce4cf9b90bd15dfdef699d"

Alternatively, if a devstack environment is used, these values are available
through "openrc" file under the "devstack_install_root" directory and can be
configured as:

.. sourcecode:: console

    $ source <devstack_install_root>/openrc

3. Upload an image to the Image service
---------------------------------------

You will need to upload a virtual machine image to the OpenStack Image
service. You can download pre-built images with vanilla Apache Hadoop
installed, or build the images yourself. This guide uses the latest available
Ubuntu upstream image, referred to as ``sahara-vanilla-latest-ubuntu.qcow2``
and the latest version of vanilla plugin as an example.
Sample images are available here:

`Sample Images <http://sahara-files.mirantis.com/images/upstream/>`_

* Download a pre-built image

**Note:** For the steps below, substitute ``<openstack_release>`` with the
appropriate OpenStack release and ``<sahara_image>`` with the image of your
choice.

.. sourcecode:: console

    $ ssh user@hostname
    $ wget http://sahara-files.mirantis.com/images/upstream/<openstack_release>/<sahara_image>.qcow2

Upload the above downloaded image into the OpenStack Image service:

.. sourcecode:: console

    $ glance image-create --name=sahara-vanilla-latest-ubuntu \
      --disk-format=qcow2 --container-format=bare < ./sahara-vanilla-latest-ubuntu.qcow2

OR

* Build the image using: `diskimage-builder script <https://github.com/openstack/sahara-image-elements/blob/master/diskimage-create/README.rst>`_

Save the image id, this will be used during the image registration with
sahara. You can get the image id using the ``glance`` command line tool
as follows:

.. sourcecode:: console

    $ glance image-list --name sahara-vanilla-latest-ubuntu
    +--------------------------------------+-------------------------------------+
    | ID                                   | Name                                |
    +--------------------------------------+-------------------------------------+
    | c119f99c-67f2-4404-9cff-f30e4b185036 | sahara-vanilla-latest-ubuntu        |
    +--------------------------------------+-------------------------------------+

    $ export IMAGE_ID="c119f99c-67f2-4404-9cff-f30e4b185036"

4. Register the image with the sahara image registry
----------------------------------------------------

Now you will begin to interact with sahara by registering the virtual
machine image in the sahara image registry.

Register the image with the username ``ubuntu``. *Note, the username
will vary depending on the source image used, for more please see*
:doc:`../userdoc/vanilla_plugin`

.. sourcecode:: console

    $ sahara image-register --id $IMAGE_ID --username ubuntu

Tag the image to inform sahara about the plugin and the version with which
it shall be used.

**Note:** For the steps below and the rest of this guide, substitute
``<plugin_version>`` with the appropriate version of your plugin.

.. sourcecode:: console

    $ sahara image-add-tag --id $IMAGE_ID --tag vanilla
    $ sahara image-add-tag --id $IMAGE_ID --tag <plugin_version>

Ensure that the image is registered correctly by querying sahara. If
registered successfully, the image will appear in the output as follows:

.. sourcecode:: console

    $ sahara image-list
    +------------------------------+--------------------------------------+----------+---------------------------+-------------+
    | name                         | id                                   | username | tags                      | description |
    +------------------------------+--------------------------------------+----------+---------------------------+-------------+
    | sahara-vanilla-latest-ubuntu | c119f99c-67f2-4404-9cff-f30e4b185036 | ubuntu   | vanilla, <plugin_version> | None        |
    +------------------------------+--------------------------------------+----------+---------------------------+-------------+

5. Create node group templates
------------------------------

Node groups are the building blocks of clusters in sahara. Before you can
begin provisioning clusters you must define a few node group templates to
describe node group configurations.

*Note, these templates assume that floating IP addresses are being used. For
more details on floating IP please see* :ref:`floating_ip_management`

If your environment does not use floating IP, omit defining floating IP in
the template below.

Sample templates can be found here:

`Sample Templates <https://github.com/openstack/sahara/tree/master/sahara/plugins/default_templates/>`_

Create a file named ``my_master_template_create.json`` with the following
content:

.. sourcecode:: json

    {
        "plugin_name": "vanilla",
        "hadoop_version": "<plugin_version>",
        "node_processes": [
            "namenode",
            "resourcemanager",
            "hiveserver"
        ],
        "name": "vanilla-default-master",
        "floating_ip_pool": "public",
        "flavor_id": "2",
        "auto_security_group": true
    }

Create a file named ``my_worker_template_create.json`` with the following
content:

.. sourcecode:: json

    {
        "plugin_name": "vanilla",
        "hadoop_version": "<plugin_version>",
        "node_processes": [
            "nodemanager",
            "datanode"
        ],
        "name": "vanilla-default-worker",
        "floating_ip_pool": "public",
        "flavor_id": "2",
        "auto_security_group": true
    }

Use the ``sahara`` client to upload the node group templates:

.. sourcecode:: console

    $ sahara node-group-template-create --json my_master_template_create.json
    $ sahara node-group-template-create --json my_worker_template_create.json

List the available node group templates to ensure that they have been
added properly:

.. sourcecode:: console

    $ sahara node-group-template-list
    +------------------------+--------------------------------------+-------------+---------------------------------------+-------------+
    | name                   | id                                   | plugin_name | node_processes                        | description |
    +------------------------+--------------------------------------+-------------+---------------------------------------+-------------+
    | vanilla-default-master | 9d3b5b2c-d5d5-4d16-8a93-a568d29c6569 | vanilla     | namenode, resourcemanager, hiveserver | None        |
    | vanilla-default-worker | 1aa4a397-cb1e-4f38-be18-7f65fa0cc2eb | vanilla     | nodemanager, datanode                 | None        |
    +------------------------+--------------------------------------+-------------+---------------------------------------+-------------+

Save the id for the master and worker node group templates as they will be
used during cluster template creation.
For example:

* Master node group template id: ``9d3b5b2c-d5d5-4d16-8a93-a568d29c6569``
* Worker node group template id: ``1aa4a397-cb1e-4f38-be18-7f65fa0cc2eb``

6. Create a cluster template
----------------------------

The last step before provisioning the cluster is to create a template
that describes the node groups of the cluster.

Create a file named ``my_cluster_template_create.json`` with the following
content:

.. sourcecode:: json

    {
        "plugin_name": "vanilla",
        "hadoop_version": "<plugin_version>",
        "node_groups": [
            {
                "name": "worker",
                "count": 2,
                "node_group_template_id": "1aa4a397-cb1e-4f38-be18-7f65fa0cc2eb"
            },
            {
                "name": "master",
                "count": 1,
                "node_group_template_id": "9d3b5b2c-d5d5-4d16-8a93-a568d29c6569"
            }
        ],
        "name": "vanilla-default-cluster",
        "cluster_configs": {}
    }

Upload the Cluster template using the ``sahara`` command line tool:

.. sourcecode:: console

    $ sahara cluster-template-create --json my_cluster_template_create.json

Save the cluster template id for use in the cluster provisioning command. The
cluster id can be found in the output of the creation command or by listing
the cluster templates as follows:

.. sourcecode:: console

    $ sahara cluster-template-list
    +-------------------------+--------------------------------------+-------------+----------------------+-------------+
    | name                    | id                                   | plugin_name | node_groups          | description |
    +-------------------------+--------------------------------------+-------------+----------------------+-------------+
    | vanilla-default-cluster | 74add4df-07c2-4053-931f-d5844712727f | vanilla     | master: 1, worker: 2 | None        |
    +-------------------------+--------------------------------------+-------------+----------------------+-------------+

7. Create cluster
-----------------

Now you are ready to provision the cluster. This step requires a few pieces of
information that can be found by querying various OpenStack services.

Create a file named ``my_cluster_create.json`` with the following content:

.. sourcecode:: json

    {
        "name": "my-cluster-1",
        "plugin_name": "vanilla",
        "hadoop_version": "<plugin_version>",
        "cluster_template_id" : "74add4df-07c2-4053-931f-d5844712727f",
        "user_keypair_id": "my_stack",
        "default_image_id": "c119f99c-67f2-4404-9cff-f30e4b185036",
        "neutron_management_network": "8cccf998-85e4-4c5f-8850-63d33c1c6916"
    }

The parameter ``user_keypair_id`` with the value ``my_stack`` is generated by
creating a keypair. You can create your own keypair in the OpenStack
Dashboard, or through the ``nova`` command line client as follows:

.. sourcecode:: console

    $ nova keypair-add my_stack --pub-key $PATH_TO_PUBLIC_KEY

If sahara is configured to use neutron for networking, you will also need to
include the ``neutron_management_network`` parameter in
``my_cluster_create.json``. If your environment does not use neutron, you can
omit ``neutron_management_network`` above. You can determine the neutron
network id with the following command:

.. sourcecode:: console

    $ neutron net-list

Create and start the cluster:

.. sourcecode:: console

    $ sahara cluster-create --json my_cluster_create.json
    +----------------------------+-------------------------------------------------+
    | Property                   | Value                                           |
    +----------------------------+-------------------------------------------------+
    | status                     | Active                                          |
    | neutron_management_network | None                                            |
    | is_transient               | False                                           |
    | description                | None                                            |
    | user_keypair_id            | my_stack                                        |
    | updated_at                 | 2015-09-02T10:58:02                             |
    | plugin_name                | vanilla                                         |
    | provision_progress         | [{u'successful': True, u'tenant_id':            |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:41:07',          |
    |                            | u'step_type': u'Engine: create cluster',        |
    |                            | u'updated_at': u'2015-09-02T10:41:12',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Wait for    |
    |                            | instances to become active', u'total': 3,       |
    |                            | u'id': u'34b4b23e-                              |
    |                            | dc94-4253-bb36-d343a4ec1e57'}, {u'successful':  |
    |                            | True, u'tenant_id':                             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:41:05',          |
    |                            | u'step_type': u'Engine: create cluster',        |
    |                            | u'updated_at': u'2015-09-02T10:41:07',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Run         |
    |                            | instances', u'total': 3, u'id': u'401f6812      |
    |                            | -d92c-44f0-acfe-f22f4dc1c3fe'}, {u'successful': |
    |                            | True, u'tenant_id':                             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:52:12',          |
    |                            | u'step_type': u'Plugin: start cluster',         |
    |                            | u'updated_at': u'2015-09-02T10:55:02',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Await       |
    |                            | DataNodes start up', u'total': 1, u'id': u      |
    |                            | '407379af-94a4-4821-9952-14a21be06ebc'},        |
    |                            | {u'successful': True, u'tenant_id':             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:41:13',          |
    |                            | u'step_type': u'Engine: create cluster',        |
    |                            | u'updated_at': u'2015-09-02T10:48:21',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Wait for    |
    |                            | instance accessibility', u'total': 3, u'id':    |
    |                            | u'534a3a7b-2678-44f4-9562-f859fef00b1f'},       |
    |                            | {u'successful': True, u'tenant_id':             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:51:43',          |
    |                            | u'step_type': u'Plugin: start cluster',         |
    |                            | u'updated_at': u'2015-09-02T10:52:12',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Start the   |
    |                            | following process(es): DataNodes,               |
    |                            | NodeManagers', u'total': 2, u'id': u'628a995c-  |
    |                            | 316c-4eed-acbf-17076ffa34db'}, {u'successful':  |
    |                            | True, u'tenant_id':                             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:48:21',          |
    |                            | u'step_type': u'Engine: create cluster',        |
    |                            | u'updated_at': u'2015-09-02T10:48:33',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Configure   |
    |                            | instances', u'total': 3, u'id': u'7fa3987a-     |
    |                            | 636f-48a5-a34c-7a6ecd6b5a44'}, {u'successful':  |
    |                            | True, u'tenant_id':                             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:50:26',          |
    |                            | u'step_type': u'Plugin: start cluster',         |
    |                            | u'updated_at': u'2015-09-02T10:51:30',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Start the   |
    |                            | following process(es): NameNode', u'total': 1,  |
    |                            | u'id': u'8988c41f-9bef-484a-                    |
    |                            | bd93-58700f55f82b'}, {u'successful': True,      |
    |                            | u'tenant_id':                                   |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:50:14',          |
    |                            | u'step_type': u'Plugin: configure cluster',     |
    |                            | u'updated_at': u'2015-09-02T10:50:25',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Configure   |
    |                            | topology data', u'total': 1, u'id':             |
    |                            | u'bc20afb9-c44a-4825-9ac2-8bd69bf7efcc'},       |
    |                            | {u'successful': True, u'tenant_id':             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:48:33',          |
    |                            | u'step_type': u'Plugin: configure cluster',     |
    |                            | u'updated_at': u'2015-09-02T10:50:14',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Configure   |
    |                            | instances', u'total': 3, u'id': u'c0a3f2ac-     |
    |                            | 508f-4ef4-ac87-db82a4999795'}, {u'successful':  |
    |                            | True, u'tenant_id':                             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:55:02',          |
    |                            | u'step_type': u'Plugin: start cluster',         |
    |                            | u'updated_at': u'2015-09-02T10:58:01',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Start the   |
    |                            | following process(es): HiveServer', u'total':   |
    |                            | 1, u'id': u'd5ab5d4c-b8e7-4fe0-b36f-            |
    |                            | 116861bdfcb3'}, {u'successful': True,           |
    |                            | u'tenant_id':                                   |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:41:13',          |
    |                            | u'step_type': u'Engine: create cluster',        |
    |                            | u'updated_at': u'2015-09-02T10:41:13',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Assign      |
    |                            | IPs', u'total': 3, u'id':                       |
    |                            | u'd6848957-6206-4116-a310-ec458e651c12'},       |
    |                            | {u'successful': True, u'tenant_id':             |
    |                            | u'c82e4bce56ce4cf9b90bd15dfdef699d',            |
    |                            | u'created_at': u'2015-09-02T10:51:30',          |
    |                            | u'step_type': u'Plugin: start cluster',         |
    |                            | u'updated_at': u'2015-09-02T10:51:43',          |
    |                            | u'cluster_id': u'9b094131-a858-4ddb-            |
    |                            | 81a8-b71597417cad', u'step_name': u'Start the   |
    |                            | following process(es): ResourceManager',        |
    |                            | u'total': 1, u'id': u'dcd433e3-017a-            |
    |                            | 430a-8217-94cae4b813c2'}]                       |
    | use_autoconfig             | True                                            |
    | anti_affinity              | []                                              |
    | node_groups                | [{u'volume_local_to_instance': False,           |
    |                            | u'availability_zone': None, u'updated_at':      |
    |                            | u'2015-09-02T10:41:06', u'instances':           |
    |                            | [{u'instance_id': u'949da8aa-7c9e-48b3-882e-    |
    |                            | 0c7a0049100e', u'created_at':                   |
    |                            | u'2015-09-02T10:41:06', u'updated_at':          |
    |                            | u'2015-09-02T10:41:13', u'instance_name':       |
    |                            | u'cluster-3-master-001', u'management_ip':      |
    |                            | u'192.168.1.134', u'internal_ip':               |
    |                            | u'172.24.17.2', u'id': u'e27503e8-a118-4c3e-    |
    |                            | a7d7-ee64fcd4568a'}],                           |
    |                            | u'node_group_template_id': u'9d3b5b2c-          |
    |                            | d5d5-4d16-8a93-a568d29c6569',                   |
    |                            | u'volumes_per_node': 0, u'id': u'6a53f95a-c2aa- |
    |                            | 48d7-b43a-62d149c656af', u'security_groups':    |
    |                            | [6], u'shares': None, u'node_configs':          |
    |                            | {u'MapReduce': {u'mapreduce.map.memory.mb':     |
    |                            | 256, u'mapreduce.reduce.memory.mb': 512,        |
    |                            | u'yarn.app.mapreduce.am.command-opts':          |
    |                            | u'-Xmx204m', u'mapreduce.reduce.java.opts':     |
    |                            | u'-Xmx409m',                                    |
    |                            | u'yarn.app.mapreduce.am.resource.mb': 256,      |
    |                            | u'mapreduce.map.java.opts': u'-Xmx204m',        |
    |                            | u'mapreduce.task.io.sort.mb': 102}, u'YARN':    |
    |                            | {u'yarn.scheduler.minimum-allocation-mb': 256,  |
    |                            | u'yarn.scheduler.maximum-allocation-mb': 2048,  |
    |                            | u'yarn.nodemanager.vmem-check-enabled':         |
    |                            | u'false', u'yarn.nodemanager.resource.memory-   |
    |                            | mb': 2048}}, u'auto_security_group': True,      |
    |                            | u'volumes_availability_zone': None,             |
    |                            | u'volume_mount_prefix': u'/volumes/disk',       |
    |                            | u'floating_ip_pool': u'public', u'image_id':    |
    |                            | None, u'volumes_size': 0, u'is_proxy_gateway':  |
    |                            | False, u'count': 1, u'name': u'master',         |
    |                            | u'created_at': u'2015-09-02T10:41:02',          |
    |                            | u'volume_type': None, u'node_processes':        |
    |                            | [u'namenode', u'resourcemanager',               |
    |                            | u'hiveserver'], u'flavor_id': u'2',             |
    |                            | u'use_autoconfig': True},                       |
    |                            | {u'volume_local_to_instance': False,            |
    |                            | u'availability_zone': None, u'updated_at':      |
    |                            | u'2015-09-02T10:41:07', u'instances':           |
    |                            | [{u'instance_id': u'47f97841-4a17-4e18-a8eb-    |
    |                            | b4ff7dd4c3d8', u'created_at':                   |
    |                            | u'2015-09-02T10:41:06', u'updated_at':          |
    |                            | u'2015-09-02T10:41:13', u'instance_name':       |
    |                            | u'cluster-3-worker-001', u'management_ip':      |
    |                            | u'192.168.1.135', u'internal_ip':               |
    |                            | u'172.24.17.3', u'id': u'c4a02678-113b-432e-    |
    |                            | 8f91-927b8e7cfe83'}, {u'instance_id':           |
    |                            | u'a02aea39-cc1f-4a1f-8232-2470ab6e8478',        |
    |                            | u'created_at': u'2015-09-02T10:41:07',          |
    |                            | u'updated_at': u'2015-09-02T10:41:13',          |
    |                            | u'instance_name': u'cluster-3-worker-002',      |
    |                            | u'management_ip': u'192.168.1.130',             |
    |                            | u'internal_ip': u'172.24.17.4', u'id': u        |
    |                            | 'b7b2d6db-cd50-484b-8036-09820d2623f2'}],       |
    |                            | u'node_group_template_id': u'1aa4a397-cb1e-     |
    |                            | 4f38-be18-7f65fa0cc2eb', u'volumes_per_node':   |
    |                            | 0, u'id': u'b666103f-a44b-4cf8-b3ae-            |
    |                            | 7d2623c6cd18', u'security_groups': [7],         |
    |                            | u'shares': None, u'node_configs':               |
    |                            | {u'MapReduce': {u'mapreduce.map.memory.mb':     |
    |                            | 256, u'mapreduce.reduce.memory.mb': 512,        |
    |                            | u'yarn.app.mapreduce.am.command-opts':          |
    |                            | u'-Xmx204m', u'mapreduce.reduce.java.opts':     |
    |                            | u'-Xmx409m',                                    |
    |                            | u'yarn.app.mapreduce.am.resource.mb': 256,      |
    |                            | u'mapreduce.map.java.opts': u'-Xmx204m',        |
    |                            | u'mapreduce.task.io.sort.mb': 102}, u'YARN':    |
    |                            | {u'yarn.scheduler.minimum-allocation-mb': 256,  |
    |                            | u'yarn.scheduler.maximum-allocation-mb': 2048,  |
    |                            | u'yarn.nodemanager.vmem-check-enabled':         |
    |                            | u'false', u'yarn.nodemanager.resource.memory-   |
    |                            | mb': 2048}}, u'auto_security_group': True,      |
    |                            | u'volumes_availability_zone': None,             |
    |                            | u'volume_mount_prefix': u'/volumes/disk',       |
    |                            | u'floating_ip_pool': u'public', u'image_id':    |
    |                            | None, u'volumes_size': 0, u'is_proxy_gateway':  |
    |                            | False, u'count': 2, u'name': u'worker',         |
    |                            | u'created_at': u'2015-09-02T10:41:02',          |
    |                            | u'volume_type': None, u'node_processes':        |
    |                            | [u'nodemanager', u'datanode'], u'flavor_id':    |
    |                            | u'2', u'use_autoconfig': True}]                 |
    | is_public                  | False                                           |
    | management_public_key      | ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDiFXlWNVD |
    |                            | 6gJT74wherHWtgchqpvgi2aJ4fPWXP+WgB4GEKpfD7a/dWu |
    |                            | Qg9eDBQIrWvVsKgG1i9YgRTHOQ7DdwoSKUAcpEewgw927ER |
    |                            | wdJ3IV7EDu0xENUgrUgp+CwPdk94SXPg1G4oHOCbOvJYcW6 |
    |                            | /b8Ci86vH9A7Uyu2T7tbVS4ciMKfwI0Z47lzcp2qDV6W8M7 |
    |                            | neghC1mNT4k29ghgcYOzY4SxQjxp1a5Iu6RtnJ2fvHbLeMS |
    |                            | 0hgeobSZ8heQzLImrp2dbyZy74goOcwKtk9dDPV853aZrjL |
    |                            | yOsc78EgW6n2Gugu7Ks12v9QEDr4H3yTt3DNTrB5Y8tt468 |
    |                            | k2n1 Generated-by-Sahara                        |
    | status_description         |                                                 |
    | hadoop_version             | <plugin_version>                                |
    | id                         | 9b094131-a858-4ddb-81a8-b71597417cad            |
    | trust_id                   | None                                            |
    | info                       | {u'HDFS': {u'NameNode':                         |
    |                            | u'hdfs://cluster-3-master-001:9000', u'Web UI': |
    |                            | u'http://192.168.1.134:50070'}, u'YARN': {u'Web |
    |                            | UI': u'http://192.168.1.134:8088',              |
    |                            | u'ResourceManager':                             |
    |                            | u'http://192.168.1.134:8032'}}                  |
    | cluster_template_id        | 74add4df-07c2-4053-931f-d5844712727f            |
    | name                       | my-cluster-1                                    |
    | cluster_configs            | {u'HDFS': {u'dfs.replication': 2}}              |
    | created_at                 | 2015-09-02T10:41:02                             |
    | default_image_id           | c119f99c-67f2-4404-9cff-f30e4b185036            |
    | shares                     | None                                            |
    | is_protected               | False                                           |
    | tenant_id                  | c82e4bce56ce4cf9b90bd15dfdef699d                |
    +----------------------------+-------------------------------------------------+

Verify the cluster launched successfully by using the ``sahara`` command
line tool as follows:

.. sourcecode:: console

    $ sahara cluster-list
    +--------------+--------------------------------------+--------+------------+
    | name         | id                                   | status | node_count |
    +--------------+--------------------------------------+--------+------------+
    | my-cluster-1 | 9b094131-a858-4ddb-81a8-b71597417cad | Active | 3          |
    +--------------+--------------------------------------+--------+------------+

The cluster creation operation may take several minutes to complete. During
this time the "status" returned from the previous command may show states
other than "Active".

8. Run a MapReduce job to check Hadoop installation
---------------------------------------------------

Check that your Hadoop installation is working properly by running an
example job on the cluster manually.

* Login to NameNode (usually master node) via ssh with ssh-key used above:

.. sourcecode:: console

    $ ssh -i my_stack.pem ubuntu@<namenode_ip>

* Switch to the hadoop user:

.. sourcecode:: console

    $ sudo su hadoop

* Go to the shared hadoop directory and run the simplest MapReduce example:

.. sourcecode:: console

    $ cd /opt/hadoop-<plugin_version>/share/hadoop/mapreduce
    $ /opt/hadoop-<plugin_version>/bin/hadoop jar hadoop-mapreduce-examples-<plugin_version>.jar pi 10 100

Congratulations! Your Hadoop cluster is ready to use, running on your
OpenStack cloud.
