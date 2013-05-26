Savanna v0.1.1 quickstart guide
===============================

1. Install Savanna
------------------

* If you want to hack follow :doc:`devref/development.environment`.
* If you want just to install and use Savanna follow :doc:`installation.guide`.

2. Image setup
--------------

2.1. Go to OpenStack management node or you can configure ENV at another machine:

.. sourcecode:: bash

    ssh user@hostname

2.2. Download tarball from the following URL:

.. sourcecode:: bash

    wget http://savanna-files.mirantis.com/savanna-0.1-hdp-img.tar.gz

2.3. Unpack image and import it into Glance:

.. sourcecode:: bash

    tar -xzf savanna-0.1-hdp-img.tar.gz
    glance image-create --name=vanilla-hadoop.image --disk-format=qcow2 --container-format=bare < ./savanna-0.1-hdp-img.img

You should see the output similar to the following:

.. sourcecode:: bash

    +------------------+--------------------------------------+
    | Property         | Value                                |
    +------------------+--------------------------------------+
    | checksum         | e5c77ac14b916de552199f09548adc2a     |
    | container_format | bare                                 |
    | created_at       | 2013-03-11T14:52:09                  |
    | deleted          | False                                |
    | deleted_at       | None                                 |
    | disk_format      | qcow2                                |
    | id               | 7989fd9a-5e30-49af-affa-dea4d7b23b9f |
    | is_public        | False                                |
    | min_disk         | 0                                    |
    | min_ram          | 0                                    |
    | name             | vanilla-hadoop.image                 |
    | owner            | 6b26f08455ec449ea7a2d3da75339255     |
    | protected        | False                                |
    | size             | 1675296768                           |
    | status           | active                               |
    | updated_at       | 2013-03-11T14:53:05                  |
    +------------------+--------------------------------------+


3. Savanna API SETUP
--------------------

Now Savanna service is running. Further steps show how you can verify from console that Savanna API works properly.

3.1. First install httpie program. It allows you to send http requests to Savanna API service.

.. sourcecode:: bash

    pip httpie

**Note:** sure you can use another HTTP client like curl to send requests to Savanna service

3.2. Then you need to get authentification token from OpenStack Keystone service.
This steps assumes you have keystone client configured:

.. sourcecode:: bash

    keystone token-get


If authentication succeed, output will be as follows:

.. sourcecode:: bash

    Configuration has been loaded from 'etc/savanna/savanna.conf'
    User: admin
    Password: swordfish
    Tenant: admin
    Auth URL: http://172.18.79.139:35357/v2.0/
    Auth succeed: True
    Auth token: d61e47a1423d477f9c77ecb23c64d424
    Tenant [admin] id: 0677a89acc834e38bf8bb41665912416

**Note:** Save the token because you have to supply it with every request to Savanna in X-Auth-Token header.
You will also use tenant id in request URL

3.3. Send http request to the Savanna service:

.. sourcecode:: bash

    http http://{savanna_api_ip}:8080/v0.2/{tenant_id}/node-templates X-Auth-Token:{auth_token}

Where:

* savanna_api_ip - hostname where Savanna API service is running
* tenant_id - id of the tenant for which you got token in previous item
* auth_token - token obtained in previous item

For example:

.. sourcecode:: bash

    http http://10.0.0.2:8080/v0.2/0677a89acc834e38bf8bb41665912416/node-templates X-Auth-Token:d61e47a1423d477f9c77ecb23c64d424

Output of this command will look as follows:

.. sourcecode:: bash

    HTTP/1.1 200 OK
    Content-Length: 1936
    Content-Type: application/json
    Date: Mon, 11 Mar 2013 17:17:03 GMT

.. sourcecode:: json

    {
        "node_templates": [
            {
                //Non-empty list of Node Templates
            }
    }

4. Hadoop Cluster startup
-------------------------

4.1. Send the POST request to Savanna API to create Hadoop Cluster.

Create file with name ``cluster_create.json`` and fill it with the following content:

.. sourcecode:: json

    {
        "cluster": {
            "name": "hdp",
            "node_templates": {
                "jt_nn.small": 1,
                "tt_dn.small": 3
            },
            "base_image_id": "image id"
        }
    }

Where:

* "name" - name of the cluster being created
* "jt_nn.small": 1 and "tt_dn.small": 3 - names and numbers of Node Templates for Hadoop NameNodes and JobTracker; DataNodes and TaskTrackers.

You can list available node templates by sending the following request to Savanna API:

.. sourcecode:: bash

    http http://{savanna_api_ip}:8080/v0.2/{tenant-id}/node-templates X-Auth-Token:{auth_token}

* "base_image_id" - OpenStack image id of image which was downloaded in the Item 2.

You can see image id in the OpenStack UI or by calling the following command of the OS Glance service:

.. sourcecode:: bash

    glance image-list

After creating the file you can send the request:

.. sourcecode:: bash

    http http://{savanna_api_ip}:8080/v0.2/{tenant-id}/clusters X-Auth-Token:{auth_token} < cluster_create.json

Response for this request will look like:

.. sourcecode:: json

    {
        "cluster": {
            "status": "Starting",
            "node_templates": {
                "jt_nn.small": 1,
                "tt_dn.small": 3
            },
            "service_urls": {},
            "name": "hdp",
            "nodes": [],
            "id": "254d8a8c483046ab9209d7993cad2da2",
            "base_image_id": "7989fd9a-5e30-49af-affa-dea4d7b23b9f"
        }
    }


4.2. If the response in the 3.1. was ``202 ACCEPTED`` then you can check status of new cluster:

.. sourcecode:: bash

    http http://{savanna_api_ip}:8080/v0.2/{tenant-id}/clusters/{cluster_id} X-Auth-Token:{auth_token}

Where "cluster_id" - id of created cluster. In our example above it the id is "254d8a8c483046ab9209d7993cad2da2"

Initially the cluster will be in "Starting" state, but eventually (in several minutes) you should get response with status "Active", like the following:

.. sourcecode:: json

    {
        "cluster": {
            "status": "Active",
            "node_templates": {
                "jt_nn.small": 1,
                "tt_dn.small": 3
            },
            "service_urls": {
                "namenode": "http://172.18.79.196:50070",
                "jobtracker": "http://172.18.79.196:50030"
            },
            "name": "hdp",
            "nodes": [
                {
                    "node_template": {
                        "id": "d19264649a5e47f98d1fcecccefbf748",
                        "name": "tt_dn.small"
                    },
                    "vm_id": "2a145a8b-0414-4d88-8335-9f3722d41724"
                },
                {
                    "node_template": {
                        "id": "d19264649a5e47f98d1fcecccefbf748",
                        "name": "tt_dn.small"
                    },
                    "vm_id": "c968c5d5-5825-4521-82b5-1c730ab8b1e4"
                },
                {
                    "node_template": {
                        "id": "d19264649a5e47f98d1fcecccefbf748",
                        "name": "tt_dn.small"
                    },
                    "vm_id": "6be15767-ff4e-4e49-9ff7-fb4b65a868d6"
                },
                {
                    "node_template": {
                        "id": "e675e9720f1e47dea5027ed7c13cc665",
                        "name": "jt_nn.small"
                    },
                    "vm_id": "11d120b2-f501-435f-a2f6-515fbacd86cf"
                }
            ],
            "id": "254d8a8c483046ab9209d7993cad2da2",
            "base_image_id": "7989fd9a-5e30-49af-affa-dea4d7b23b9f"
        }
    }

4.3. So you recieved NameNode's and JobTracker's URLs like this:

.. sourcecode:: json

    "service_urls": {
        "namenode": "http://NameNode_IP:50070",
        "jobtracker": "http://JobTracker_IP:50030"
    }
    
and you actually could access them via browser

4.4. To check that your Hadoop installation works correctly:

* Go to NameNode via ssh:

.. sourcecode:: bash

    ssh root@NameNode_IP
    using 'swordfish' as password

* Switch to hadoop user:

.. sourcecode:: bash

    su hadoop

* Go to hadoop home directory and run the simpliest MapReduce example:

.. sourcecode:: bash

    cd ~
    ./run_simple_MR_job.sh

* You can check status of MR job running by browsing JobTracker url:

.. sourcecode:: bash

    "jobtracker": "http://JobTracker_IP:50030"

Congratulations! Now you have Hadoop cluster ready on the OpenStack cloud!

5. Keystone endpoints setup
---------------------------

To use CLI tools, such as OpenStack's python clients, we should specify
environment variables with addresses and credentials. Let's mind that we have
keystone at `127.0.0.1:5000` with tenant `admin`, credentials `admin`:`nova`
and Savanna API at `127.0.0.1:8080`. Here is a list of commands to set env:

.. sourcecode:: bash

    export OS_AUTH_URL=http://127.0.0.1:5000/v2.0/
    export OS_TENANT_NAME=admin
    export OS_USERNAME=admin
    export OS_PASSWORD=nova

We should create service in Keystone:

.. sourcecode:: bash

    keystone service-create --name=savanna --type=mapreduce --description="Savanna Elastic Hadoop Service"

And then we should create endpoint for created service:

.. sourcecode:: bash

    keystone endpoint-create \
        --region RegionOne \
        --service-id=<SERVICE_ID> \
        --publicurl="http://127.0.0.1:8080/v0.2/%(tenant_id)s" \
        --internalurl="http://127.0.0.1:8080/v0.2/%(tenant_id)s" \
        --adminurl="http://127.0.0.1:8080/v0.2/%(tenant_id)s"

Now Keystone know endpoints of service `mapreduce`.
