Quickstart guide
================

This guide will help you to setup vanilla Hadoop cluster using
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
Now you can get authentication token from OpenStack Keystone service.

.. sourcecode:: console

    $ keystone token-get


If authentication succeed, output will be as follows:

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

You can download pre-built images with vanilla Apache Hadoop or build this
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


* OR build image using :doc:`../userdoc/diskimagebuilder`.


Save image id. You can get image id from command ``glance image-list``:

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

    $ sahara image-register --image-id $IMAGE_ID --username ubuntu

* Tag the image:

.. sourcecode:: console

    $ sahara image-add-tag --image-id $IMAGE_ID --tag vanilla
    $ sahara image-add-tag --image-id $IMAGE_ID --tag 1.2.1

* Make sure that image is registered correctly:

.. sourcecode:: console

    $ sahara image-list

* Output should look like:

.. sourcecode:: console

    $ sahara image-list
    +----------------+---------------+----------+----------------+-------------+
    | name           | id            | username | tags           | description |
    +----------------+---------------+----------+----------------+-------------+
    | sahara-iceh... | 3f9fc...6919b | ubuntu   | vanilla, 1.2.1 | None        |
    +----------------+---------------+----------+----------------+-------------+


5. Setup NodeGroup templates
----------------------------

Create file with name ``ng_master_template_create.json`` and fill it with the
following content:

.. sourcecode:: json

    {
        "name": "test-master-tmpl",
        "flavor_id": "2",
        "plugin_name": "vanilla",
        "hadoop_version": "1.2.1",
        "node_processes": ["jobtracker", "namenode"],
        "auto_security_group": True
    }

Create file with name ``ng_worker_template_create.json`` and fill it with the
following content:

.. sourcecode:: json

    {
        "name": "test-worker-tmpl",
        "flavor_id": "2",
        "plugin_name": "vanilla",
        "hadoop_version": "1.2.1",
        "node_processes": ["tasktracker", "datanode"],
        "auto_security_group": True
    }

Send POST requests to Sahara API to upload NodeGroup templates:

.. sourcecode:: console

    $ http $SAHARA_URL/node-group-templates X-Auth-Token:$AUTH_TOKEN \
     < ng_master_template_create.json

    $ http $SAHARA_URL/node-group-templates X-Auth-Token:$AUTH_TOKEN \
     < ng_worker_template_create.json


You can list available NodeGroup templates by sending the following request to
Sahara API:

.. sourcecode:: console

    $ http $SAHARA_URL/node-group-templates X-Auth-Token:$AUTH_TOKEN

Output should look like:

.. sourcecode:: json

    {
        "node_group_templates": [
            {
                "created": "2013-07-07T18:53:55",
                "flavor_id": "2",
                "hadoop_version": "1.2.1",
                "id": "b38227dc-64fe-42bf-8792-d1456b453ef3",
                "name": "demo-master",
                "node_configs": {},
                "node_processes": [
                    "jobtracker",
                    "namenode"
                ],
                "plugin_name": "vanilla",
                "updated": "2013-07-07T18:53:55",
                "volume_mount_prefix": "/volumes/disk",
                "volumes_per_node": 0,
                "volumes_size": 10,
                "security_groups": [],
                "auto_security_group": True
            },
            {
                "created": "2013-07-07T18:54:00",
                "flavor_id": "2",
                "hadoop_version": "1.2.1",
                "id": "634827b9-6a18-4837-ae15-5371d6ecf02c",
                "name": "demo-worker",
                "node_configs": {},
                "node_processes": [
                    "tasktracker",
                    "datanode"
                ],
                "plugin_name": "vanilla",
                "updated": "2013-07-07T18:54:00",
                "volume_mount_prefix": "/volumes/disk",
                "volumes_per_node": 0,
                "volumes_size": 10,
                "security_groups": [],
                "auto_security_group": True
            }
        ]
    }


Save id for the master and worker NodeGroup templates. For example:

* Master NodeGroup template id: ``b38227dc-64fe-42bf-8792-d1456b453ef3``
* Worker NodeGroup template id: ``634827b9-6a18-4837-ae15-5371d6ecf02c``


6. Setup Cluster Template
-------------------------

Create file with name ``cluster_template_create.json`` and fill it with the
following content:

.. sourcecode:: json

    {
        "name": "demo-cluster-template",
        "plugin_name": "vanilla",
        "hadoop_version": "1.2.1",
        "node_groups": [
            {
                "name": "master",
                "node_group_template_id": "b1ac3f04-c67f-445f-b06c-fb722736ccc6",
                "count": 1
            },
            {
                "name": "workers",
                "node_group_template_id": "dbc6147e-4020-4695-8b5d-04f2efa978c5",
                "count": 2
            }
        ]
    }

Send POST request to Sahara API to upload Cluster template:

.. sourcecode:: console

    $ http $SAHARA_URL/cluster-templates X-Auth-Token:$AUTH_TOKEN \
     < cluster_template_create.json

Save template id. For example ``ce897df2-1610-4caa-bdb8-408ef90561cf``.

7. Create cluster
-----------------

Create file with name ``cluster_create.json`` and fill it with the
following content:

.. sourcecode:: json

    {
        "name": "cluster-1",
        "plugin_name": "vanilla",
        "hadoop_version": "1.2.1",
        "cluster_template_id" : "ce897df2-1610-4caa-bdb8-408ef90561cf",
        "user_keypair_id": "stack",
        "default_image_id": "3f9fc974-b484-4756-82a4-bff9e116919b"
    }

There is a parameter ``user_keypair_id`` with value ``stack``. You can create
your own keypair in in Horizon UI, or using the command line client:

.. sourcecode:: console

    nova keypair-add stack --pub-key $PATH_TO_PUBLIC_KEY


Send POST request to Sahara API to create and start the cluster:

.. sourcecode:: console

    $ http $SAHARA_URL/clusters X-Auth-Token:$AUTH_TOKEN \
     < cluster_create.json


Once cluster started, you'll get similar output:

.. sourcecode:: json

    {
        "clusters": [
            {
                "anti_affinity": [],
                "cluster_configs": {},
                "cluster_template_id": "ce897df2-1610-4caa-bdb8-408ef90561cf",
                "created": "2013-07-07T19:01:51",
                "default_image_id": "3f9fc974-b484-4756-82a4-bff9e116919b",
                "hadoop_version": "1.2.1",
                "id": "c5e755a2-b3f9-417b-948b-e99ed7fbf1e3",
                "info": {
                    "HDFS": {
                        "Web UI": "http://172.24.4.225:50070"
                    },
                    "MapReduce": {
                        "Web UI": "http://172.24.4.225:50030"
                    }
                },
                "name": "cluster-1",
                "node_groups": [
                    {
                        "count": 1,
                        "created": "2013-07-07T19:01:51",
                        "flavor_id": "999",
                        "instances": [
                            {
                                "created": "2013-07-07T19:01:51",
                                "instance_id": "4f6dc715-9c65-4d74-bddd-5f1820e6ce02",
                                "instance_name": "cluster-1-master-001",
                                "internal_ip": "10.0.0.5",
                                "management_ip": "172.24.4.225",
                                "updated": "2013-07-07T19:06:07",
                                "volumes": []
                            }
                        ],
                        "name": "master",
                        "node_configs": {},
                        "node_group_template_id": "b38227dc-64fe-42bf-8792-d1456b453ef3",
                        "node_processes": [
                            "jobtracker",
                            "namenode"
                        ],
                        "updated": "2013-07-07T19:01:51",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_per_node": 0,
                        "volumes_size": 10,
                        "security_groups": ["a314895b-d2ee-431d-a26b-7c37b45894c9"],
                        "auto_security_group": True
                    },
                    {
                        "count": 2,
                        "created": "2013-07-07T19:01:51",
                        "flavor_id": "999",
                        "instances": [
                            {
                                "created": "2013-07-07T19:01:52",
                                "instance_id": "11089dd0-8832-4473-a835-d3dd36bc3d00",
                                "instance_name": "cluster-1-workers-001",
                                "internal_ip": "10.0.0.6",
                                "management_ip": "172.24.4.227",
                                "updated": "2013-07-07T19:06:07",
                                "volumes": []
                            },
                            {
                                "created": "2013-07-07T19:01:52",
                                "instance_id": "d59ee54f-19e6-401b-8662-04a156ba811f",
                                "instance_name": "cluster-1-workers-002",
                                "internal_ip": "10.0.0.7",
                                "management_ip": "172.24.4.226",
                                "updated": "2013-07-07T19:06:07",
                                "volumes": []
                            }
                        ],
                        "name": "workers",
                        "node_configs": {},
                        "node_group_template_id": "634827b9-6a18-4837-ae15-5371d6ecf02c",
                        "node_processes": [
                            "tasktracker",
                            "datanode"
                        ],
                        "updated": "2013-07-07T19:01:51",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_per_node": 0,
                        "volumes_size": 10,
                        "security_groups": ["b260407f-a566-43bf-a010-7e8b23953dc6"],
                        "auto_security_group": True
                    }
                ],
                "plugin_name": "vanilla",
                "status": "Active",
                "updated": "2013-07-07T19:06:24",
                "user_keypair_id": "stack"
            }
        ]
    }

8. Run MapReduce job
--------------------

To check that your Hadoop installation works correctly:

* Go to NameNode via ssh:

.. sourcecode:: console

    $ ssh ubuntu@<namenode_ip>

* Switch to hadoop user:

.. sourcecode:: console

    $ sudo su hadoop

* Go to hadoop home directory and run the simpliest MapReduce example:

.. sourcecode:: console

    $ cd /usr/share/hadoop
    $ hadoop jar hadoop-examples-1.2.1.jar pi 10 100

Congratulations! Now you have Hadoop cluster ready on the OpenStack cloud!
