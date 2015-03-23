Quickstart guide
================

This guide will help you setup a vanilla Hadoop cluster using
:doc:`../restapi/rest_api_v1.0`.

1. Install Sahara
-----------------

* If you want to hack the code follow :doc:`development.environment`.
* If you just want to install and use Sahara follow :doc:`../userdoc/installation.guide`.


2. Keystone endpoints setup
---------------------------

To use CLI tools, such as OpenStack's python clients, we should specify
environment variables with addresses and credentials. Let's mind that we have
keystone at ``127.0.0.1:5000`` with tenant ``admin``, credentials ``admin:nova``
and Sahara API at ``127.0.0.1:8386``. Here is a list of commands to set env:

.. sourcecode:: console

   $ export OS_AUTH_URL=http://127.0.0.1:5000/v2.0/
   $ export OS_TENANT_NAME=admin
   $ export OS_USERNAME=admin
   $ export OS_PASSWORD=nova


You can append these lines to the ``.bashrc`` and execute ``source .bashrc``.
Now you can get an authentication token from the OpenStack Keystone service.

.. sourcecode:: console

   $ keystone token-get


If authentication succeeds, the output will be as follows:

.. sourcecode:: console

    +-----------+----------------------------------+
    |  Property |              Value               |
    +-----------+----------------------------------+
    |  expires  |       2013-07-08T15:21:18Z       |
    |     id    | dd92e3cdb4e1462690cd444d6b01b746 |
    | tenant_id | 62bd2046841e4e94a87b4a22aa886c13 |
    |  user_id  | 720fb87141a14fd0b204f977f5f02512 |
    +-----------+----------------------------------+

Save ``tenant_id`` which is obviously your Tenant ID and ``id`` which is your
authentication token (X-Auth-Token):

.. sourcecode:: console

   $ export AUTH_TOKEN="dd92e3cdb4e1462690cd444d6b01b746"
   $ export TENANT_ID="62bd2046841e4e94a87b4a22aa886c13"


3. Upload image to Glance
-------------------------

You can download pre-built images with vanilla Apache Hadoop or build the
images yourself:

* Download and install pre-built image with Ubuntu 13.10

.. sourcecode:: console

   $ ssh user@hostname
   $ wget http://sahara-files.mirantis.com/sahara-icehouse-vanilla-1.2.1-ubuntu-13.10.qcow2
   $ glance image-create --name=sahara-icehouse-vanilla-1.2.1-ubuntu-13.10 \
      --disk-format=qcow2 --container-format=bare < ./sahara-icehouse-vanilla-1.2.1-ubuntu-13.10.qcow2


* OR with Fedora 20

.. sourcecode:: console

   $ ssh user@hostname
   $ wget http://sahara-files.mirantis.com/sahara-icehouse-vanilla-1.2.1-fedora-20.qcow2
   $ glance image-create --name=sahara-icehouse-vanilla-1.2.1-fedora-20 \
      --disk-format=qcow2 --container-format=bare < ./sahara-icehouse-vanilla-1.2.1-fedora-20.qcow2


* OR build the image using :doc:`../userdoc/diskimagebuilder`.


Save the image id. You can get the image id from the command ``glance image-list``:

.. sourcecode:: console

   $ glance image-list --name sahara-icehouse-vanilla-1.2.1-ubuntu-13.10
    +--------------------------------------+---------------------------------------------+
    | ID                                   | Name                                        |
    +--------------------------------------+---------------------------------------------+
    | 3f9fc974-b484-4756-82a4-bff9e116919b | sahara-icehouse-vanilla-1.2.1-ubuntu-13.10  |
    +--------------------------------------+---------------------------------------------+

   $ export IMAGE_ID="3f9fc974-b484-4756-82a4-bff9e116919b"


4. Register image in Image Registry
-----------------------------------

* Now we will actually start to interact with Sahara.

* Register the image with username ``ubuntu``.

.. sourcecode:: console

   $ sahara image-register --id $IMAGE_ID --username ubuntu

* Tag the image:

.. sourcecode:: console

   $ sahara image-add-tag --id $IMAGE_ID --tag vanilla
   $ sahara image-add-tag --id $IMAGE_ID --tag 1.2.1

* Make sure the image is registered correctly:

.. sourcecode:: console

   $ sahara image-list

* Output should look like:

.. sourcecode:: console

    +----------------+---------------+----------+----------------+-------------+
    | name           | id            | username | tags           | description |
    +----------------+---------------+----------+----------------+-------------+
    | sahara-iceh... | 3f9fc...6919b | ubuntu   | vanilla, 1.2.1 | None        |
    +----------------+---------------+----------+----------------+-------------+


5. Setup NodeGroup templates
----------------------------

Create a file named ``ng_master_template_create.json`` with the following content:

.. sourcecode:: json

    {
        "name": "test-master-tmpl",
        "flavor_id": "2",
        "plugin_name": "vanilla",
        "hadoop_version": "1.2.1",
        "node_processes": ["jobtracker", "namenode"],
        "auto_security_group": true
    }

Create a file named ``ng_worker_template_create.json`` with the following content:

.. sourcecode:: json

    {
        "name": "test-worker-tmpl",
        "flavor_id": "2",
        "plugin_name": "vanilla",
        "hadoop_version": "1.2.1",
        "node_processes": ["tasktracker", "datanode"],
        "auto_security_group": true
    }

Use the Sahara client to upload NodeGroup templates:

.. sourcecode:: console

   $ sahara node-group-template-create --json ng_master_template_create.json
   $ sahara node-group-template-create --json ng_worker_template_create.json

List the available NodeGroup templates:

.. sourcecode:: console

   $ sahara node-group-template-list
    +--------+--------------------------------------+-------------+-------------------------------------------------+-------------+
    | name   | id                                   | plugin_name | node_processes                                  | description |
    +--------+--------------------------------------+-------------+-------------------------------------------------+-------------+
    | master | b38227dc-64fe-42bf-8792-d1456b453ef3 | vanilla     | namenode, resourcemanager, oozie, historyserver | None        |
    | worker | 634827b9-6a18-4837-ae15-5371d6ecf02c | vanilla     | datanode, nodemanager                           | None        |
    +--------+--------------------------------------+-------------+-------------------------------------------------+-------------+

Save the id for the master and worker NodeGroup templates. For example:

* Master NodeGroup template id: ``b38227dc-64fe-42bf-8792-d1456b453ef3``
* Worker NodeGroup template id: ``634827b9-6a18-4837-ae15-5371d6ecf02c``


6. Setup Cluster Template
-------------------------

Create a file named ``cluster_template_create.json`` with the following content:

.. sourcecode:: json

    {
        "name": "demo-cluster-template",
        "plugin_name": "vanilla",
        "hadoop_version": "1.2.1",
        "node_groups": [
            {
                "name": "master",
                "node_group_template_id": "b38227dc-64fe-42bf-8792-d1456b453ef3",
                "count": 1
            },
            {
                "name": "workers",
                "node_group_template_id": "634827b9-6a18-4837-ae15-5371d6ecf02c",
                "count": 2
            }
        ]
    }

Upload the Cluster template:

.. sourcecode:: console

   $ sahara cluster-template-create --json cluster_template_create.json

Save the template id. For example ``ce897df2-1610-4caa-bdb8-408ef90561cf``.

7. Create cluster
-----------------

Create a file named ``cluster_create.json`` with the following content:

.. sourcecode:: json

    {
        "name": "cluster-1",
        "plugin_name": "vanilla",
        "hadoop_version": "1.2.1",
        "cluster_template_id" : "ce897df2-1610-4caa-bdb8-408ef90561cf",
        "user_keypair_id": "stack",
        "default_image_id": "3f9fc974-b484-4756-82a4-bff9e116919b"
        "neutron_management_network": "8cccf998-85e4-4c5f-8850-63d33c1c6916"
    }

There is a parameter ``user_keypair_id`` with value ``stack``. You can create
your own keypair in Horizon UI, or using the command line client:

.. sourcecode:: console

   $ nova keypair-add stack --pub-key $PATH_TO_PUBLIC_KEY

If ``use_neutron = true`` is set in sahara.conf, you will also need to include
the ``neutron_management_network`` parameter in ``cluster_create.json``. Instances
will get fixed IPs in this network. Find the Neutron network id:

.. sourcecode:: console

   $ neutron net-list


Create and start the cluster:

.. sourcecode:: console

   $ sahara cluster-create --json cluster_create.json
    +----------------------------+-------------------------------------------------+
    | Property                   | Value                                           |
    +----------------------------+-------------------------------------------------+
    | status                     | Validating                                      |
    | neutron_management_network | 8cccf998-85e4-4c5f-8850-63d33c1c6916            |
    | is_transient               | False                                           |
    | description                | None                                            |
    | user_keypair_id            | stack                                           |
    | updated_at                 | 2013-07-07T19:01:51                             |
    | plugin_name                | vanilla                                         |
    | anti_affinity              | []                                              |
    | node_groups                | [{u'count': 1, u'name': u'master',              |
    |                            | u'instances': [], u'volume_mount_prefix':       |
    |                            | u'/volumes/disk', u'created_at': u'2015-03-17   |
    |                            | 18:33:42', u'updated_at': None,                 |
    |                            | u'floating_ip_pool': u'70b8c139-096b-4b3b-b29f- |
    |                            | f42b16316758', u'image_id': None,               |
    |                            | u'volumes_size': 0, u'node_configs': {},        |
    |                            | u'node_group_template_id': u'09946a01-7973-4f63 |
    |                            | -9aca-7fc6d498d8a6', u'volumes_per_node': 0,    |
    |                            | u'node_processes': [u'jobtracker',              |
    |                            | u'namenode'], u'auto_security_group': True,     |
    |                            | u'security_groups': None, u'flavor_id': u'2'},  |
    |                            | {u'count': 2, u'name': u'workers',              |
    |                            | u'instances': [], u'volume_mount_prefix':       |
    |                            | u'/volumes/disk', u'created_at': u'2015-03-17   |
    |                            | 18:33:42', u'updated_at': None,                 |
    |                            | u'floating_ip_pool': u'70b8c139-096b-4b3b-b29f- |
    |                            | f42b16316758', u'image_id': None,               |
    |                            | u'volumes_size': 0, u'node_configs': {},        |
    |                            | u'node_group_template_id': u'ceb017bd-0568-42e9 |
    |                            | -890b-03eb298dc99f', u'volumes_per_node': 0,    |
    |                            | u'node_processes': [u'tasktracker',             |
    |                            | u'datanode'], u'auto_security_group': True,     |
    |                            | u'security_groups': None, u'flavor_id': u'2'}]  |
    | management_public_key      | ssh-rsa BBBBB3NzaB1yc2EAAAADAQABAAABAQCziEF+3oJ |
    |                            | ki6Fd1rvuiducJ470DN9ZFagiFbLfcwqu7TNKee10uice5P |
    |                            | KmvpusXMaL5LiZFTHafbFJfNUlah90yGpfsYqbcx2dMNqoU |
    |                            | EF4ZvEVO7RVU8jCe7DXBEkBFGQ1x/v17vyaxIJ8AqnFVSuu |
    |                            | FgfcHuihLAC250ZlfNWMcoFhUy6MsBocoxCF6MVal5Xt8nw |
    |                            | Y8o8xTQwd/f4wbAeAE3P0TaOCpXpMxxLL/hMDALekdxs1Gh |
    |                            | Mk0k5rbj4oD9AKx8+/jucIxS6mmwqWwwqo7jmy2jIsukOGZ |
    |                            | 1LdeNe0ctOX56k1LoZybzMzT6NbgUwfuIRbOwuryy2QbWwV |
    |                            | gX6t Generated by Sahara                        |
    | status_description         |                                                 |
    | hadoop_version             | 1.2.1                                           |
    | id                         | c5e755a2-b3f9-417b-948b-e99ed7fbf1e3            |
    | trust_id                   | None                                            |
    | info                       | {}                                              |
    | cluster_template_id        | ce897df2-1610-4caa-bdb8-408ef90561cf            |
    | name                       | cluster-1                                       |
    | cluster_configs            | {}                                              |
    | created_at                 | 2013-07-07T19:01:51                             |
    | default_image_id           | 3f9fc974-b484-4756-82a4-bff9e116919b            |
    | tenant_id                  | 3fd7266fb3b547b1a45307b481bcadfd                |
    +----------------------------+-------------------------------------------------+

Verify the cluster launched successfully:

.. sourcecode:: console

   $ sahara cluster-list
    +-----------+--------------------------------------+--------+------------+
    | name      | id                                   | status | node_count |
    +-----------+--------------------------------------+--------+------------+
    | cluster-1 | c5e755a2-b3f9-417b-948b-e99ed7fbf1e3 | Active | 3          |
    +-----------+--------------------------------------+--------+------------+


8. Run MapReduce job
--------------------

To check that your Hadoop installation works correctly:

* Go to NameNode via ssh:

.. sourcecode:: console

   $ ssh ubuntu@<namenode_ip>

* Switch to hadoop user:

.. sourcecode:: console

   $ sudo su hadoop

* Go to the hadoop home directory and run the simplest MapReduce example:

.. sourcecode:: console

   $ cd /usr/share/hadoop
   $ hadoop jar hadoop-examples-1.2.1.jar pi 10 100

Congratulations! Now you have the Hadoop cluster ready on the OpenStack cloud!
