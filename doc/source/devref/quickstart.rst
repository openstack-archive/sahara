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
    $ export OS_PROJECT_NAME=admin
    $ export OS_USERNAME=admin
    $ export OS_PASSWORD=nova

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

    $ openstack image create sahara-vanilla-latest-ubuntu --disk-format qcow2 \
        --container-format bare --file sahara-vanilla-latest-ubuntu.qcow2
    +------------------+--------------------------------------+
    | Field            | Value                                |
    +------------------+--------------------------------------+
    | checksum         | 3da49911332fc46db0c5fb7c197e3a77     |
    | container_format | bare                                 |
    | created_at       | 2016-02-29T10:15:04.000000           |
    | deleted          | False                                |
    | deleted_at       | None                                 |
    | disk_format      | qcow2                                |
    | id               | 71b9eeac-c904-4170-866a-1f833ea614f3 |
    | is_public        | False                                |
    | min_disk         | 0                                    |
    | min_ram          | 0                                    |
    | name             | sahara-vanilla-latest-ubuntu         |
    | owner            | 057d23cddb864759bfa61d730d444b1f     |
    | properties       |                                      |
    | protected        | False                                |
    | size             | 1181876224                           |
    | status           | active                               |
    | updated_at       | 2016-02-29T10:15:41.000000           |
    | virtual_size     | None                                 |
    +------------------+--------------------------------------+

OR

* Build the image using: `diskimage-builder script <https://github.com/openstack/sahara-image-elements/blob/master/diskimage-create/README.rst>`_

Remember the image name or save the image ID, this will be used during the
image registration with sahara. You can get the image ID using the
``openstack`` command line tool as follows:

.. sourcecode:: console

    $ openstack image list --property name=sahara-vanilla-latest-ubuntu
    +--------------------------------------+------------------------------+
    | ID                                   | Name                         |
    +--------------------------------------+------------------------------+
    | 71b9eeac-c904-4170-866a-1f833ea614f3 | sahara-vanilla-latest-ubuntu |
    +--------------------------------------+------------------------------+

4. Register the image with the sahara image registry
----------------------------------------------------

Now you will begin to interact with sahara by registering the virtual
machine image in the sahara image registry.

Register the image with the username ``ubuntu``. *Note, the username
will vary depending on the source image used, for more please see*
:doc:`../userdoc/vanilla_plugin`

.. sourcecode:: console

    $ openstack dataprocessing image register sahara-vanilla-latest-ubuntu \
        --username ubuntu

Tag the image to inform sahara about the plugin and the version with which
it shall be used.

**Note:** For the steps below and the rest of this guide, substitute
``<plugin_version>`` with the appropriate version of your plugin.

.. sourcecode:: console

    $ openstack dataprocessing image tags add sahara-vanilla-latest-ubuntu \
        --tags vanilla <plugin_version>
    +-------------+--------------------------------------+
    | Field       | Value                                |
    +-------------+--------------------------------------+
    | Description | None                                 |
    | Id          | 71b9eeac-c904-4170-866a-1f833ea614f3 |
    | Name        | sahara-vanilla-latest-ubuntu         |
    | Status      | ACTIVE                               |
    | Tags        | <plugin_version>, vanilla            |
    | Username    | ubuntu                               |
    +-------------+--------------------------------------+

5. Create node group templates
------------------------------

Node groups are the building blocks of clusters in sahara. Before you can
begin provisioning clusters you must define a few node group templates to
describe node group configurations.

You can get information about available plugins with the following command:

.. sourcecode:: console

    $ openstack dataprocessing plugin list

Also you can get information about available services for a particular plugin
with the ``plugin show`` command. For example:

.. sourcecode:: console

    $ openstack dataprocessing plugin show vanilla --plugin-version <plugin_version>
    +---------------------+-----------------------------------------------------------------------------------------------------------------------+
    | Field               | Value                                                                                                                 |
    +---------------------+-----------------------------------------------------------------------------------------------------------------------+
    | Description         | The Apache Vanilla plugin provides the ability to launch upstream Vanilla Apache Hadoop cluster without any           |
    |                     | management consoles. It can also deploy the Oozie component.                                                          |
    | Name                | vanilla                                                                                                               |
    | Required image tags | <plugin_version>, vanilla                                                                                                        |
    | Title               | Vanilla Apache Hadoop                                                                                                 |
    |                     |                                                                                                                       |
    | Service:            | Available processes:                                                                                                  |
    |                     |                                                                                                                       |
    | HDFS                | datanode, namenode, secondarynamenode                                                                                 |
    | Hadoop              |                                                                                                                       |
    | Hive                | hiveserver                                                                                                            |
    | JobFlow             | oozie                                                                                                                 |
    | MapReduce           | historyserver                                                                                                         |
    | YARN                | nodemanager, resourcemanager                                                                                          |
    +---------------------+-----------------------------------------------------------------------------------------------------------------------+

*Note, these commands assume that floating IP addresses are being used. For
more details on floating IP please see* :ref:`floating_ip_management`

Create a master node group template with the command:

.. sourcecode:: console

    $ openstack dataprocessing node group template create \
        --name vanilla-default-master --plugin vanilla \
        --plugin-version <plugin_version> --processes namenode resourcemanager \
        --flavor 2 --auto-security-group --floating-ip-pool <pool-id>
    +---------------------+--------------------------------------+
    | Field               | Value                                |
    +---------------------+--------------------------------------+
    | Auto security group | True                                 |
    | Availability zone   | None                                 |
    | Flavor id           | 2                                    |
    | Floating ip pool    | dbd8d1aa-6e8e-4a35-a77b-966c901464d5 |
    | Id                  | 0f066e14-9a73-4379-bbb4-9d9347633e31 |
    | Is default          | False                                |
    | Is protected        | False                                |
    | Is proxy gateway    | False                                |
    | Is public           | False                                |
    | Name                | vanilla-default-master               |
    | Node processes      | namenode, resourcemanager            |
    | Plugin name         | vanilla                              |
    | Security groups     | None                                 |
    | Use autoconfig      | False                                |
    | Version             | <plugin_version>                     |
    | Volumes per node    | 0                                    |
    +---------------------+--------------------------------------+

Create a worker node group template with the command:

.. sourcecode:: console

    $ openstack dataprocessing node group template create \
        --name vanilla-default-worker --plugin vanilla \
        --plugin-version <plugin_version> --processes datanode nodemanager \
        --flavor 2 --auto-security-group --floating-ip-pool <pool-id>
    +---------------------+--------------------------------------+
    | Field               | Value                                |
    +---------------------+--------------------------------------+
    | Auto security group | True                                 |
    | Availability zone   | None                                 |
    | Flavor id           | 2                                    |
    | Floating ip pool    | dbd8d1aa-6e8e-4a35-a77b-966c901464d5 |
    | Id                  | 6546bf44-0590-4539-bfcb-99f8e2c11efc |
    | Is default          | False                                |
    | Is protected        | False                                |
    | Is proxy gateway    | False                                |
    | Is public           | False                                |
    | Name                | vanilla-default-worker               |
    | Node processes      | datanode, nodemanager                |
    | Plugin name         | vanilla                              |
    | Security groups     | None                                 |
    | Use autoconfig      | False                                |
    | Version             | <plugin_version>                     |
    | Volumes per node    | 0                                    |
    +---------------------+--------------------------------------+

Alternatively you can create node group templates from JSON files:

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
            "resourcemanager"
        ],
        "name": "vanilla-default-master",
        "floating_ip_pool": "<floating_ip_pool_id>",
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
        "floating_ip_pool": "<floating_ip_pool_id>",
        "flavor_id": "2",
        "auto_security_group": true
    }

Use the ``openstack`` client to upload the node group templates:

.. sourcecode:: console

    $ openstack dataprocessing node group template create \
        --json my_master_template_create.json
    $ openstack dataprocessing node group template create \
        --json my_worker_template_create.json

List the available node group templates to ensure that they have been
added properly:

.. sourcecode:: console

    $ openstack dataprocessing node group template list --name vanilla-default
    +------------------------+--------------------------------------+-------------+--------------------+
    | Name                   | Id                                   | Plugin name | Version            |
    +------------------------+--------------------------------------+-------------+--------------------+
    | vanilla-default-master | 0f066e14-9a73-4379-bbb4-9d9347633e31 | vanilla     | <plugin_version>   |
    | vanilla-default-worker | 6546bf44-0590-4539-bfcb-99f8e2c11efc | vanilla     | <plugin_version>   |
    +------------------------+--------------------------------------+-------------+--------------------+

Remember the name or save the ID for the master and worker node group templates
as they will be used during cluster template creation.

For example:

* vanilla-default-master: ``0f066e14-9a73-4379-bbb4-9d9347633e31``
* vanilla-default-worker: ``6546bf44-0590-4539-bfcb-99f8e2c11efc``

6. Create a cluster template
----------------------------

The last step before provisioning the cluster is to create a template
that describes the node groups of the cluster.

Create a cluster template with the command:

.. sourcecode:: console

    $ openstack dataprocessing cluster template create \
        --name vanilla-default-cluster \
        --node-groups vanilla-default-master:1 vanilla-default-worker:3

    +----------------+----------------------------------------------------+
    | Field          | Value                                              |
    +----------------+----------------------------------------------------+
    | Anti affinity  |                                                    |
    | Description    | None                                               |
    | Id             | 9d871ebd-88a9-40af-ae3e-d8c8f292401c               |
    | Is default     | False                                              |
    | Is protected   | False                                              |
    | Is public      | False                                              |
    | Name           | vanilla-default-cluster                            |
    | Node groups    | vanilla-default-master:1, vanilla-default-worker:3 |
    | Plugin name    | vanilla                                            |
    | Use autoconfig | False                                              |
    | Version        | <plugin_version>                                   |
    +----------------+----------------------------------------------------+

Alternatively you can create cluster template from JSON file:

Create a file named ``my_cluster_template_create.json`` with the following
content:

.. sourcecode:: json

    {
        "plugin_name": "vanilla",
        "hadoop_version": "<plugin_version>",
        "node_groups": [
            {
                "name": "worker",
                "count": 3,
                "node_group_template_id": "6546bf44-0590-4539-bfcb-99f8e2c11efc"
            },
            {
                "name": "master",
                "count": 1,
                "node_group_template_id": "0f066e14-9a73-4379-bbb4-9d9347633e31"
            }
        ],
        "name": "vanilla-default-cluster",
        "cluster_configs": {}
    }

Upload the cluster template using the ``openstack`` command line tool:

.. sourcecode:: console

    $ openstack dataprocessing cluster template create --json my_cluster_template_create.json

Remember the cluster template name or save the cluster template ID for use in
the cluster provisioning command. The cluster ID can be found in the output of
the creation command or by listing the cluster templates as follows:

.. sourcecode:: console

    $ openstack dataprocessing cluster template list --name vanilla-default
    +-------------------------+--------------------------------------+-------------+--------------------+
    | Name                    | Id                                   | Plugin name | Version            |
    +-------------------------+--------------------------------------+-------------+--------------------+
    | vanilla-default-cluster | 9d871ebd-88a9-40af-ae3e-d8c8f292401c | vanilla     | <plugin_version>   |
    +-------------------------+--------------------------------------+-------------+--------------------+

7. Create cluster
-----------------

Now you are ready to provision the cluster. This step requires a few pieces of
information that can be found by querying various OpenStack services.

Create a cluster with the command:

.. sourcecode:: console

    $ openstack dataprocessing cluster create --name my-cluster-1 \
        --cluster-template vanilla-default-cluster --user-keypair my_stack \
        --neutron-network private --image sahara-vanilla-latest-ubuntu

    +----------------------------+----------------------------------------------------+
    | Field                      | Value                                              |
    +----------------------------+----------------------------------------------------+
    | Anti affinity              |                                                    |
    | Cluster template id        | 9d871ebd-88a9-40af-ae3e-d8c8f292401c               |
    | Description                |                                                    |
    | Id                         | 1f0dc6f7-6600-495f-8f3a-8ac08cdb3afc               |
    | Image                      | 71b9eeac-c904-4170-866a-1f833ea614f3               |
    | Is protected               | False                                              |
    | Is public                  | False                                              |
    | Is transient               | False                                              |
    | Name                       | my-cluster-1                                       |
    | Neutron management network | fabe9dae-6fbd-47ca-9eb1-1543de325efc               |
    | Node groups                | vanilla-default-master:1, vanilla-default-worker:3 |
    | Plugin name                | vanilla                                            |
    | Status                     | Validating                                         |
    | Use autoconfig             | False                                              |
    | User keypair id            | my_stack                                           |
    | Version                    | <plugin_version>                                   |
    +----------------------------+----------------------------------------------------+

Alternatively you can create cluster template from JSON file:

Create a file named ``my_cluster_create.json`` with the following content:

.. sourcecode:: json

    {
        "name": "my-cluster-1",
        "plugin_name": "vanilla",
        "hadoop_version": "<plugin_version>",
        "cluster_template_id" : "9d871ebd-88a9-40af-ae3e-d8c8f292401c",
        "user_keypair_id": "my_stack",
        "default_image_id": "71b9eeac-c904-4170-866a-1f833ea614f3",
        "neutron_management_network": "fabe9dae-6fbd-47ca-9eb1-1543de325efc"
    }

The parameter ``user_keypair_id`` with the value ``my_stack`` is generated by
creating a keypair. You can create your own keypair in the OpenStack
Dashboard, or through the ``openstack`` command line client as follows:

.. sourcecode:: console

    $ openstack keypair create my_stack --public-key $PATH_TO_PUBLIC_KEY

If sahara is configured to use neutron for networking, you will also need to
include the ``--neutron-network`` argument in the ``cluster create`` command or
``neutron_management_network`` parameter in ``my_cluster_create.json``. If
your environment does not use neutron, you can omit ``--neutron-network`` or
the ``neutron_management_network`` above. You can determine the neutron network
id with the following command:

.. sourcecode:: console

    $ openstack network list

Create and start the cluster:

.. sourcecode:: console

    $ openstack dataprocessing cluster create --json my_cluster_create.json

Verify the cluster status by using the ``openstack`` command
line tool as follows:

.. sourcecode:: console

    $ openstack dataprocessing cluster show my-cluster-1 -c Status
    +--------+--------+
    | Field  | Value  |
    +--------+--------+
    | Status | Active |
    +--------+--------+

The cluster creation operation may take several minutes to complete. During
this time the "status" returned from the previous command may show states
other than ``Active``. A cluster also can be created with the ``wait`` flag. In
that case the cluster creation command will not be finished until the cluster
will be moved to the ``Active`` state.

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
