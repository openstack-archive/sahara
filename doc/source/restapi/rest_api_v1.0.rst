Sahara REST API v1.0
*********************

.. note::

    REST API v1.0 corresponds to Sahara v0.2.X

1 General API information
=========================

This section contains base info about the Sahara REST API design.

1.1 Authentication and Authorization
------------------------------------

The Sahara API uses the Keystone Identity Service as the default authentication service.
When Keystone is enabled, users who submit requests to the Sahara service must provide an authentication token
in the X-Auth-Token request header. A user can obtain the token by authenticating to the Keystone endpoint.
For more information about Keystone, see the OpenStack Identity Developer Guide.

Also with each request a user must specify the OpenStack tenant in the url path, for example: '/v1.0/{tenant_id}/clusters'.
Sahara will perform the requested operation in the specified tenant using the provided credentials. Therefore, clusters may be created and managed only within tenants to which the user has access.

1.2 Request / Response Types
----------------------------

The Sahara API supports the JSON data serialization format.
This means that for requests that contain a body, the Content-Type header must be set to the MIME type value
"application/json". Also, clients should accept JSON serialized responses by specifying the Accept header
with the MIME type value "application/json" or adding the ".json" extension to the resource name.
The default response format is "application/json" if the client does not specify an Accept header
or append the ".json" extension in the URL path.

Example:

.. sourcecode:: http

    GET /v1.0/{tenant_id}/clusters.json

or

.. sourcecode:: http

    GET /v1.0/{tenant_id}/clusters
    Accept: application/json

1.3 Faults
----------

The Sahara API returns an error response if a failure occurs while processing a request.
Sahara uses only standard HTTP error codes. 4xx errors indicate problems in the particular
request being sent from the client and 5xx errors indicate server-side problems.

The response body will contain richer information about the cause of the error.
An error response follows the format illustrated by the following example:

.. sourcecode:: http

    HTTP/1.1 400 BAD REQUEST
    Content-type: application/json
    Content-length: 126

    {
        "error_name": "CLUSTER_NAME_ALREADY_EXISTS",
        "error_message": "Cluster with name 'test-cluster' already exists",
        "error_code": 400
    }


The 'error_code' attribute is an HTTP response code. The 'error_name' attribute
indicates the generic error type without any concrete ids or names, etc.
The last attribute, 'error_message', contains a human readable error description.

2 Plugins
=========

**Description**

A Plugin object provides information about what Hadoop distribution/version it can install, and what configurations can be set for the cluster.

**Plugins ops**

+-----------------+-----------------------------------------------------------------------------------+-----------------------------------------------------+
| Verb            | URI                                                                               | Description                                         |
+=================+===================================================================================+=====================================================+
| GET             | /v1.0/{tenant_id}/plugins                                                         | Lists all plugins registered in Sahara.             |
+-----------------+-----------------------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.0/{tenant_id}/plugins/{plugin_name}                                           | Shows short information about specified plugin.     |
+-----------------+-----------------------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.0/{tenant_id}/plugins/{plugin_name}/{version}                                 | Shows detailed information for plugin, like         |
|                 |                                                                                   | node_processes, required_image_tags and configs.    |
+-----------------+-----------------------------------------------------------------------------------+-----------------------------------------------------+
| POST            | /v1.0/{tenant_id}/plugins/{plugin_name}/{version}/convert-config/{template-name}  | Converts file-based cluster config to Cluster       |
|                 |                                                                                   | Template Object                                     |
+-----------------+-----------------------------------------------------------------------------------+-----------------------------------------------------+

**Examples**

2.1 List all Plugins
--------------------

.. http:get:: /v1.0/{tenant_id}/plugins

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all plugins.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/plugins

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "plugins": [
                {
                    "description": "This plugin provides an ability to launch vanilla Apache Hadoop cluster without any management consoles.",
                    "versions": [
                        "1.2.1"
                    ],
                    "name": "vanilla",
                    "title": "Vanilla Apache Hadoop"
                }
            ]
        }

2.2 Short Plugin information
----------------------------

.. http:get:: /v1.0/{tenant_id}/plugins/{plugin_name}

Normal Response Code: 200 (OK)

Errors: none

This operation returns short plugin description.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/plugins/vanilla

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "plugin": {
                "title": "Vanilla Apache Hadoop",
                "description": "This plugin provides an ability to launch vanilla Apache Hadoop cluster without any management consoles.",
                "name": "vanilla",
                "versions": [
                    "1.2.1"
                ]
            }
        }

2.3 Detailed Plugin information
-------------------------------

.. http:get:: /v1.0/{tenant_id}/plugins/{plugin_name}/{version}

Normal Response Code: 200 (OK)

Errors: none

This operation returns detailed plugin description.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/plugins/vanilla/1.2.1

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "plugin": {
                "node_processes": {
                    "HDFS": [
                        "namenode",
                        "datanode",
                        "secondarynamenode"
                    ],
                    "MapReduce": [
                        "tasktracker",
                        "jobtracker"
                    ]
                },
                "description": "This plugin provides an ability to launch vanilla Apache Hadoop cluster without any management consoles.",
                "versions": [
                    "1.2.1"
                ],
                "required_image_tags": [
                    "vanilla",
                    "1.2.1"
                ],
                "configs": [
                    {
                        "default_value": "/tmp/hadoop-${user.name}",
                        "name": "hadoop.tmp.dir",
                        "priority": 2,
                        "config_type": "string",
                        "applicable_target": "HDFS",
                        "is_optional": true,
                        "scope": "node",
                        "description": "A base for other temporary directories."
                    },
                    {
                        "default_value": true,
                        "name": "hadoop.native.lib",
                        "priority": 2,
                        "config_type": "bool",
                        "applicable_target": "HDFS",
                        "is_optional": true,
                        "scope": "node",
                        "description": "Should native hadoop libraries, if present, be used."
                    },
                ],
                "title": "Vanilla Apache Hadoop",
                "name": "vanilla"
            }
        }

2.4 Convert configuration file
------------------------------

.. http:post:: /v1.0/{tenant_id}/plugins/{plugin_name}/{version}/convert-config/{template-name}

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns short plugin description.

The request body should contain configuration file.

**Example**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/plugins/some-plugin/1.1/convert-config/tname

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster_template": {
                "name": "cluster-template",
                "cluster_configs": {
                    "HDFS": {},
                    "MapReduce": {},
                    "general": {}
                },
                "plugin_name": "some-plugin",
                "anti_affinity": [],
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "namenode",
                            "jobtracker"
                        ],
                    },
                    {
                        "count": 3,
                        "name": "worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ],
                    }
                ],
                "hadoop_version": "1.1",
                "id": "c365b7dd-9b11-492d-a119-7ae023c19b51",
                "description": "Converted Cluster Template"
            }
        }

3 Image Registry
================

**Description**

The Image Registry is a tool for managing images. Each plugin provides a list of required tags an image should have.
Sahara also requires a username to login into an instance's OS for remote operations execution.

The Image Registry provides an ability to add/remove tags to images and define the OS username.

**Image Registry ops**

+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| Verb            | URI                                                               | Description                                         |
+=================+===================================================================+=====================================================+
| GET             | /v1.0/{tenant_id}/images                                          | Lists all images registered in Image Registry       |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.0/{tenant_id}/images?tags=tag1&tags=tag2                      | Lists all images with both tag1 and tag2            |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.0/{tenant_id}/images/{image_id}                               | Shows information about specified Image.            |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| POST            | /v1.0/{tenant_id}/images/{image_id}                               | Registers specified Image in Image Registry         |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| DELETE          | /v1.0/{tenant_id}/images/{image_id}                               | Removes specified Image from Image Registry         |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| POST            | /v1.0/{tenant_id}/images/{image_id}/tag                           | Adds tags to specified Image                        |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| POST            | /v1.0/{tenant_id}/images/{image_id}/untag                         | Removes tags for specified Image                    |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+

**Examples**

3.1 List all Images
-------------------

.. http:get:: /v1.0/{tenant_id}/images

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all registered images.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/images

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "images": [
                {
                    "status": "ACTIVE",
                    "username": "ec2-user",
                    "name": "fedoraSwift_hadoop_sahara_v02",
                    "tags": [
                        "vanilla",
                        "1.2.1"
                    ],
                    "minDisk": 0,
                    "progress": 100,
                    "minRam": 0,
                    "metadata": {
                        "_sahara_tag_vanilla": "True",
                        "_sahara_tag_1.2.1": "True",
                        "_sahara_username": "ec2-user"
                    },
                    "id": "daa50c37-b11b-4f3d-a586-e5dcd0a4110f"
                }
            ]
        }

3.2 List Images with specified tags
-----------------------------------

.. http:get:: /v1.0/{tenant_id}/images?tags=tag1&tags=tag2

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of images with specified tags.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/images?tags=vanilla

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "images": [
                {
                    "status": "ACTIVE",
                    "username": "ec2-user",
                    "name": "fedoraSwift_hadoop_sahara_v02",
                    "tags": [
                        "vanilla",
                        "1.2.1"
                    ],
                    "minDisk": 0,
                    "progress": 100,
                    "minRam": 0,
                    "metadata": {
                        "_sahara_tag_vanilla": "True",
                        "_sahara_tag_1.2.1": "True",
                        "_sahara_username": "ec2-user"
                    },
                    "id": "daa50c37-b11b-4f3d-a586-e5dcd0a4110f"
                }
            ]
        }



3.3 Show Image
--------------

.. http:get:: /v1.0/{tenant_id}/images/{image_id}

Normal Response Code: 200 (OK)

Errors: none

This operation shows information about the requested Image.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/images/daa50c37-b11b-4f3d-a586-e5dcd0a4110f

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "image": {
                "status": "ACTIVE",
                "username": "ec2-user",
                "name": "fedoraSwift_hadoop_sahara_v02",
                "tags": [
                    "vanilla",
                    "1.2.1"
                ],
                "minDisk": 0,
                "progress": 100,
                "minRam": 0,
                "metadata": {
                    "_sahara_tag_vanilla": "True",
                    "_sahara_tag_1.2.1": "True",
                    "_sahara_username": "ec2-user"
                },
                "id": "daa50c37-b11b-4f3d-a586-e5dcd0a4110f"
            }
        }


3.4 Register Image
------------------

.. http:post:: /v1.0/{tenant_id}/images/{image_id}

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns the registered image.

**Example**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/images/daa50c37-b11b-4f3d-a586-e5dcd0a4110f

    .. sourcecode:: json

        {
            "username": "ec2-user",
            "description": "Fedora image"
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "image": {
                "status": "ACTIVE",
                "username": "ec2-user",
                "name": "fedoraSwift_hadoop_sahara_v02",
                "tags": [],
                "minDisk": 0,
                "progress": 100,
                "minRam": 0,
                "metadata": {
                    "_sahara_username": "ec2-user",
                    "_sahara_description": "Fedora image"
                },
                "id": "daa50c37-b11b-4f3d-a586-e5dcd0a4110f"
            }
        }

3.5 Delete Image
----------------

.. http:delete:: /v1.0/{tenant_id}/images/{image_id}

Normal Response Code: 204 (NO CONTENT)

Errors: none

Remove an Image from the Image Registry

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara/v1.0/775181/images/daa50c37-b11b-4f3d-a586-e5dcd0a4110f

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json

3.6 Add Tags to Image
---------------------

.. http:post:: /v1.0/{tenant_id}/images/{image_id}/tag

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns the updated image.

Add Tags to Image.

**Example**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/images/daa50c37-b11b-4f3d-a586-e5dcd0a4110f/tag

    .. sourcecode:: json

        {
            "tags": ["tag1", "some_other_tag"]
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "image": {
                "status": "ACTIVE",
                "username": "ec2-user",
                "name": "fedoraSwift_hadoop_sahara_v02",
                "tags": ["tag1", "some_other_tag"],
                "minDisk": 0,
                "progress": 100,
                "minRam": 0,
                "metadata": {
                    "_sahara_username": "ec2-user",
                    "_sahara_description": "Fedora image",
                    "_sahara_tag_tag1": "True",
                    "_sahara_tag_some_other_tag": "True"
                },
                "id": "daa50c37-b11b-4f3d-a586-e5dcd0a4110f"
            }
        }

3.7 Remove Tags from Image
--------------------------

.. http:post:: /v1.0/{tenant_id}/images/{image_id}/untag

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns the updated image.

Removes Tags from Image.

**Example**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/images/daa50c37-b11b-4f3d-a586-e5dcd0a4110f/untag

    .. sourcecode:: json

        {
            "tags": ["unnecessary_tag"],
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "image": {
                "status": "ACTIVE",
                "username": "ec2-user",
                "name": "fedoraSwift_hadoop_sahara_v02",
                "tags": ["tag1"],
                "minDisk": 0,
                "progress": 100,
                "minRam": 0,
                "metadata": {
                    "_sahara_username": "ec2-user",
                    "_sahara_description": "Fedora image",
                    "_sahara_tag_tag1": "True"
                },
                "id": "daa50c37-b11b-4f3d-a586-e5dcd0a4110f"
            }
        }

4 Node Group Templates
======================

**Description**

A Node Group Template is a template for configuring a group of nodes.
A Node Group Template contains a list of processes that will be launched on each node.
Also node scoped configurations can be defined in a Node Group Template.

**Node Group Templates ops**

+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+
| Verb            | URI                                                               | Description                                           |
+=================+===================================================================+=======================================================+
| GET             | /v1.0/{tenant_id}/node-group-templates                            | Lists all Node Group Templates.                       |
+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+
| GET             | /v1.0/{tenant_id}/node-group-templates/<node_group_template_id>   | Shows Information about specified Node Group Template |
|                 |                                                                   | by id                                                 |
+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+
| POST            | /v1.0/{tenant_id}/node-group-templates                            | Creates a new Node Group Template.                    |
+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+
| DELETE          | /v1.0/{tenant_id}/node-group-templates/<node_group_template_id>   | Deletes an existing Node Group Template by id.        |
+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+

**Examples**

4.1 List all Node Group Templates
---------------------------------

.. http:get:: /v1.0/{tenant_id}/node-group-templates

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all Node Group Templates.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/node-group-templates

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "node_group_templates": [
                {
                    "name": "master",
                    "volume_mount_prefix": "/volumes/disk",
                    "plugin_name": "vanilla",
                    "volumes_size": 10,
                    "node_processes": [
                        "namenode",
                        "jobtracker"
                    ],
                    "flavor_id": "42",
                    "volumes_per_node": 0,
                    "node_configs": {
                        "HDFS": {},
                        "MapReduce": {}
                    },
                    "hadoop_version": "1.2.1",
                    "id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9",
                    "description": ""
                },
                {
                    "name": "worker",
                    "volume_mount_prefix": "/volumes/disk",
                    "plugin_name": "vanilla",
                    "volumes_size": 10,
                    "node_processes": [
                        "datanode",
                        "tasktracker"
                    ],
                    "flavor_id": "42",
                    "volumes_per_node": 0,
                    "node_configs": {
                        "HDFS": {},
                        "MapReduce": {}
                    },
                    "hadoop_version": "1.2.1",
                    "id": "6bbaba84-d936-4e76-9381-987d3568cf4c",
                    "description": ""
                }
            ]
        }

4.2 Show Node Group Template
----------------------------


.. http:get:: /v1.0/{tenant_id}/node-group-templates/{node_group_template_id}

Normal Response Code: 200 (OK)

Errors: none

This operation shows information about a specified Node Group Template.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/node-group-templates/ea34d320-09d7-4dc1-acbf-75b57cec81c9

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "node_group_template": {
                "name": "master",
                "volume_mount_prefix": "/volumes/disk",
                "plugin_name": "vanilla",
                "volumes_size": 10,
                "node_processes": [
                    "namenode",
                    "jobtracker"
                ],
                "flavor_id": "42",
                "volumes_per_node": 0,
                "floating_ip_pool": "public",
                "node_configs": {
                    "HDFS": {},
                    "MapReduce": {}
                },
                "hadoop_version": "1.2.1",
                "id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9",
                "description": ""
            }
        }

4.3 Create Node Group Template
------------------------------

.. http:post:: /v1.0/{tenant_id}/node-group-templates

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns created Node Group Template.

**Example without configurations**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/node-group-templates

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "1.2.1",
            "node_processes": [
                "namenode",
                "jobtracker"
            ],
            "name": "master",
            "floating_ip_pool", "public",
            "flavor_id": "42"
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "node_group_template": {
                "name": "master",
                "volume_mount_prefix": "/volumes/disk",
                "plugin_name": "vanilla",
                "volumes_size": 10,
                "node_processes": [
                    "namenode",
                    "jobtracker"
                ],
                "flavor_id": "42",
                "volumes_per_node": 0,
                "floating_ip_pool", "public",
                "node_configs": {},
                "hadoop_version": "1.2.1",
                "id": "ddefda09-9ab9-4555-bf48-e996243af6f2"
            }
        }

**Example with configurations**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/node-group-templates

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "1.2.1",
            "node_processes": [
                "datanode",
                "tasktracker"
            ],
            "name": "worker",
            "flavor_id": "42",
            "node_configs": {
                "HDFS": {
                    "data_node_heap_size": 1024
                },
                "MapReduce": {
                    "task_tracker_heap_size": 1024
                }
            }
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "node_group_template": {
                "name": "worker",
                "volume_mount_prefix": "/volumes/disk",
                "plugin_name": "vanilla",
                "volumes_size": 10,
                "node_processes": [
                    "datanode",
                    "tasktracker"
                ],
                "flavor_id": "42",
                "volumes_per_node": 0,
                "node_configs": {
                    "HDFS": {
                        "data_node_heap_size": 1024
                    },
                    "MapReduce": {
                        "task_tracker_heap_size": 1024
                    }
                },
                "hadoop_version": "1.2.1",
                "id": "060afabe-f4b3-487e-8d48-65c5bb5eb79e"
            }
        }


4.4 Delete Node Group Template
------------------------------

.. http:delete:: /v1.0/{tenant_id}/node-group-templates/{node_group_template_id}

Normal Response Code: 204 (NO CONTENT)

Errors: none

Remove Node Group Template

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara/v1.0/775181/node-group-templates/060afabe-f4b3-487e-8d48-65c5bb5eb79e

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json

5 Cluster Templates
===================

**Description**

A Cluster Template is a template for configuring a Hadoop cluster.
A Cluster Template contains a list of node groups with number of instances in each.
Also cluster scoped configurations can be defined in a Cluster Template.

**Cluster Templates ops**

+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+
| Verb            | URI                                                               | Description                                           |
+=================+===================================================================+=======================================================+
| GET             | /v1.0/{tenant_id}/cluster-templates                               | Lists all Cluster Templates.                          |
+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+
| GET             | /v1.0/{tenant_id}/cluster-templates/<cluster_template_id>         | Shows Information about specified Cluster Template    |
|                 |                                                                   | by id                                                 |
+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+
| POST            | /v1.0/{tenant_id}/cluster-templates                               | Creates a new Cluster Template.                       |
+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+
| DELETE          | /v1.0/{tenant_id}/cluster-templates/<cluster_template_id>         | Deletes an existing Cluster Template by id.           |
+-----------------+-------------------------------------------------------------------+-------------------------------------------------------+

**Examples**

5.1 List all Cluster Templates
------------------------------

.. http:get:: /v1.0/{tenant_id}/cluster-templates

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all Cluster Templates.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/cluster-templates

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster_templates": [
                {
                    "name": "cluster-template",
                    "cluster_configs": {
                        "HDFS": {},
                        "MapReduce": {},
                        "general": {}
                    },
                    "plugin_name": "vanilla",
                    "anti_affinity": [],
                    "node_groups": [
                        {
                            "count": 1,
                            "name": "master",
                            "volume_mount_prefix": "/volumes/disk",
                            "volumes_size": 10,
                            "node_configs": {
                                "HDFS": {},
                                "MapReduce": {}
                            },
                            "flavor_id": "42",
                            "volumes_per_node": 0,
                            "node_processes": [
                                "namenode",
                                "jobtracker"
                            ],
                            "node_group_template_id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9"
                        },
                        {
                            "count": 3,
                            "name": "worker",
                            "volume_mount_prefix": "/volumes/disk",
                            "volumes_size": 10,
                            "node_configs": {
                                "HDFS": {},
                                "MapReduce": {}
                            },
                            "flavor_id": "42",
                            "volumes_per_node": 0,
                            "node_processes": [
                                "datanode",
                                "tasktracker"
                            ],
                            "node_group_template_id": "6bbaba84-d936-4e76-9381-987d3568cf4c"
                        }
                    ],
                    "hadoop_version": "1.2.1",
                    "id": "c365b7dd-9b11-492d-a119-7ae023c19b51",
                    "description": ""
                }
            ]
        }

5.2 Show Cluster Template
-------------------------


.. http:get:: /v1.0/{tenant_id}/cluster-templates/{cluster_template_id}

Normal Response Code: 200 (OK)

Errors: none

This operation shows information about a specified Cluster Template.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/cluster-templates/c365b7dd-9b11-492d-a119-7ae023c19b51

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster_template": {
                "name": "cluster-template",
                "cluster_configs": {
                    "HDFS": {},
                    "MapReduce": {},
                    "general": {}
                },
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "namenode",
                            "jobtracker"
                        ],
                        "node_group_template_id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9"
                    },
                    {
                        "count": 3,
                        "name": "worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ],
                        "node_group_template_id": "6bbaba84-d936-4e76-9381-987d3568cf4c"
                    }
                ],
                "hadoop_version": "1.2.1",
                "id": "c365b7dd-9b11-492d-a119-7ae023c19b51",
                "description": ""
            }
        }

5.3 Create Cluster Template
---------------------------

.. http:post:: /v1.0/{tenant_id}/cluster-templates

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns created Cluster Template.

**Example without configurations. Node groups taken from templates**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/cluster-templates

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "1.2.1",
            "node_groups": [
                {
                    "name": "worker",
                    "count": 3,
                    "node_group_template_id": "6bbaba84-d936-4e76-9381-987d3568cf4c"
                },
                {
                    "name": "master",
                    "count": 1,
                    "node_group_template_id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9"
                }
            ],
            "name": "cl-template",
            "neutron_management_network": "e017fdde-a2f7-41ed-b342-2d63083e7772",
            "cluster_configs": {}
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster_template": {
                "name": "cl-template",
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "node_groups": [
                    {
                        "count": 3,
                        "name": "worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ],
                        "node_group_template_id": "6bbaba84-d936-4e76-9381-987d3568cf4c"
                    },
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "namenode",
                            "jobtracker"
                        ],
                        "node_group_template_id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9"
                    }
                ],
                "neutron_management_network": "e017fdde-a2f7-41ed-b342-2d63083e7772",
                "cluster_configs": {},
                "hadoop_version": "1.2.1",
                "id": "e2ad1d5d-5fff-45e8-8c3c-34697c7cd5ac"
            }
        }

**Example with configurations and no Node Group Templates**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/node-group-templates

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "1.2.1",
            "node_groups": [
                {
                    "name": "master",
                    "count": 1,
                    "flavor_id": "42",
                    "node_processes": [
                        "namenode",
                        "jobtracker"
                    ]
                },
                {
                    "name": "worker",
                    "count": 3,
                    "flavor_id": "42",
                    "node_processes": [
                        "datanode",
                        "tasktracker"
                    ]
                }
            ],
            "name": "cl-template2",
            "cluster_configs": {
                "HDFS": {
                    "dfs.replication": 2
                }
            },
            "anti_affinity": []
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster_template": {
                "name": "cl-template2",
                "cluster_configs": {
                    "HDFS": {
                        "dfs.replication": 2
                    }
                },
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_configs": {},
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "namenode",
                            "jobtracker"
                        ]
                    },
                    {
                        "count": 3,
                        "name": "worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_configs": {},
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ]
                    }
                ],
                "hadoop_version": "1.2.1",
                "id": "9d72bc1a-8d38-493e-99f3-ebca4ec99ad8"
            }
        }


5.4 Delete Cluster Template
---------------------------

.. http:delete:: /v1.0/{tenant_id}/cluster-templates/{cluster_template_id}

Normal Response Code: 204 (NO CONTENT)

Errors: none

Remove Cluster Template

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara/v1.0/775181/cluster-templates/9d72bc1a-8d38-493e-99f3-ebca4ec99ad8

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json

6 Clusters
==========

**Description**

A Cluster object represents a Hadoop cluster.
A Cluster like a Cluster Template contains a list of node groups with the number of instances in each.
Also cluster scoped configurations can be defined in a Cluster Object.
Users should provide an OpenStack keypair to get access to cluster nodes via SSH.

**Cluster ops**

+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| Verb            | URI                                                               | Description                                            |
+=================+===================================================================+========================================================+
| GET             | /v1.0/{tenant_id}/clusters                                        | Lists all Clusters.                                    |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| GET             | /v1.0/{tenant_id}/clusters/<cluster_id>                           | Shows Information about specified Cluster by id.       |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| POST            | /v1.0/{tenant_id}/clusters                                        | Starts a new Cluster.                                  |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| PUT             | /v1.0/{tenant_id}/clusters/<cluster_id>                           | Scale existing Cluster by adding nodes or Node Groups. |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| DELETE          | /v1.0/{tenant_id}/clusters/<cluster_id>                           | Terminates an existing Cluster by id.                  |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+

**Examples**

6.1 List all Clusters
---------------------

.. http:get:: /v1.0/{tenant_id}/clusters

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all Clusters.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/clusters

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "clusters": [
                {
                    "status": "Waiting",
                    "info": {},
                    "name": "doc-cluster",
                    "cluster_configs": {
                        "HDFS": {},
                        "MapReduce": {},
                        "general": {}
                    },
                    "default_image_id": "db12c199-d0b5-47d3-8a97-e95eeaeae615",
                    "user_keypair_id": "doc-keypair",
                    "plugin_name": "vanilla",
                    "anti_affinity": [],
                    "node_groups": [
                        {
                            "count": 1,
                            "updated": "2013-07-09T09:24:44",
                            "name": "master",
                            "created": "2013-07-09T09:24:44",
                            "volume_mount_prefix": "/volumes/disk",
                            "volumes_size": 10,
                            "node_processes": [
                                "namenode",
                                "jobtracker"
                            ],
                            "flavor_id": "42",
                            "volumes_per_node": 0,
                            "node_configs": {
                                "HDFS": {},
                                "MapReduce": {}
                            },
                            "instances": [
                                {
                                    "instance_name": "doc-cluster-master-001",
                                    "instance_id": "b366f88c-bf7d-4371-a046-96179ded4c83",
                                    "volumes": []
                                }
                            ],
                            "node_group_template_id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9"
                        },
                        {
                            "count": 3,
                            "updated": "2013-07-09T09:24:44",
                            "name": "worker",
                            "created": "2013-07-09T09:24:44",
                            "volume_mount_prefix": "/volumes/disk",
                            "volumes_size": 10,
                            "node_processes": [
                                "datanode",
                                "tasktracker"
                            ],
                            "flavor_id": "42",
                            "volumes_per_node": 0,
                            "node_configs": {
                                "HDFS": {},
                                "MapReduce": {}
                            },
                            "instances": [
                                {
                                    "instance_name": "doc-cluster-worker-001",
                                    "instance_id": "f9fcd132-0534-4023-b4f6-9e10e2156299",
                                    "volumes": []
                                },
                                {
                                    "instance_name": "doc-cluster-worker-002",
                                    "instance_id": "ce486914-364c-456e-8b0e-322ad178ca9e",
                                    "volumes": []
                                },
                                {
                                    "instance_name": "doc-cluster-worker-003",
                                    "instance_id": "21312b4f-82fd-4840-8ba6-1606c7a2a75a",
                                    "volumes": []
                                }
                            ],
                            "node_group_template_id": "6bbaba84-d936-4e76-9381-987d3568cf4c"
                        }
                    ],
                    "hadoop_version": "1.2.1",
                    "id": "1bb1cced-765e-4a2b-a5b6-ac6bbb0bb798"
                }
            ]
        }

6.2 Show Cluster
----------------


.. http:get:: /v1.0/{tenant_id}/clusters/{cluster_id}

Normal Response Code: 200 (OK)

Errors: none

This operation shows information about a specified Cluster.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.0/775181/clusters/c365b7dd-9b11-492d-a119-7ae023c19b51

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster": {
                "status": "Waiting",
                "info": {},
                "name": "doc-cluster",
                "cluster_configs": {
                    "HDFS": {},
                    "MapReduce": {},
                    "general": {}
                },
                "default_image_id": "db12c199-d0b5-47d3-8a97-e95eeaeae615",
                "user_keypair_id": "doc-keypair",
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "node_groups": [
                    {
                        "count": 1,
                        "updated": "2013-07-09T09:24:44",
                        "name": "master",
                        "created": "2013-07-09T09:24:44",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "namenode",
                            "jobtracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-master-001",
                                "instance_id": "b366f88c-bf7d-4371-a046-96179ded4c83",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9"
                    },
                    {
                        "count": 3,
                        "updated": "2013-07-09T09:24:44",
                        "name": "worker",
                        "created": "2013-07-09T09:24:44",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-worker-001",
                                "instance_id": "f9fcd132-0534-4023-b4f6-9e10e2156299",
                                "volumes": []
                            },
                            {
                                "instance_name": "doc-cluster-worker-002",
                                "instance_id": "ce486914-364c-456e-8b0e-322ad178ca9e",
                                "volumes": []
                            },
                            {
                                "instance_name": "doc-cluster-worker-003",
                                "instance_id": "21312b4f-82fd-4840-8ba6-1606c7a2a75a",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "6bbaba84-d936-4e76-9381-987d3568cf4c"
                    }
                ],
                "hadoop_version": "1.2.1",
                "id": "1bb1cced-765e-4a2b-a5b6-ac6bbb0bb798"
            }
        }

6.3 Start Cluster
-----------------

.. http:post:: /v1.0/{tenant_id}/clusters

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns created Cluster.

**Example Cluster creation from template**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/clusters

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "1.2.1",
            "cluster_template_id": "1bb1cced-765e-4a2b-a5b6-ac6bbb0bb798",
            "default_image_id": "db12c199-d0b5-47d3-8a97-e95eeaeae615",
            "user_keypair_id": "doc-keypair",
            "name": "doc-cluster",
            "cluster_configs": {}
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster": {
                "status": "Waiting",
                "info": {},
                "name": "doc-cluster",
                "default_image_id": "db12c199-d0b5-47d3-8a97-e95eeaeae615",
                "user_keypair_id": "doc-keypair",
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "namenode",
                            "jobtracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-master-001",
                                "instance_id": "b366f88c-bf7d-4371-a046-96179ded4c83",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9"
                    },
                    {
                        "count": 3,
                        "updated": "2013-07-09T09:24:44",
                        "name": "worker",
                        "created": "2013-07-09T09:24:44",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-worker-001",
                                "instance_id": "f9fcd132-0534-4023-b4f6-9e10e2156299",
                                "volumes": []
                            },
                            {
                                "instance_name": "doc-cluster-worker-002",
                                "instance_id": "ce486914-364c-456e-8b0e-322ad178ca9e",
                                "volumes": []
                            },
                            {
                                "instance_name": "doc-cluster-worker-003",
                                "instance_id": "21312b4f-82fd-4840-8ba6-1606c7a2a75a",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "6bbaba84-d936-4e76-9381-987d3568cf4c"
                    }
                ],
                "cluster_configs": {
                    "HDFS": {},
                    "MapReduce": {},
                    "general": {}
                },
                "hadoop_version": "1.2.1",
                "id": "1bb1cced-765e-4a2b-a5b6-ac6bbb0bb798"
            }
        }

**Example Cluster creation from Node Groups**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/clusters

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "1.2.1",
            "default_image_id": "db12c199-d0b5-47d3-8a97-e95eeaeae615",
            "user_keypair_id": "doc-keypair",
            "node_groups": [
                {
                    "name": "master",
                    "count": 1,
                    "flavor_id": "42",
                    "node_processes": [
                        "namenode",
                        "jobtracker"
                    ]
                },
                {
                    "name": "worker",
                    "count": 3,
                    "flavor_id": "42",
                    "node_processes": [
                        "datanode",
                        "tasktracker"
                    ]
                }
            ],
            "name": "doc-cluster2",
            "cluster_configs": {
                "HDFS": {
                    "dfs.replication": 2
                }
            },
            "anti_affinity": []
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster": {
                "status": "Waiting",
                "info": {},
                "name": "doc-cluster2",
                "cluster_configs": {
                    "HDFS": {
                        "dfs.replication": 2
                    },
                    "MapReduce": {},
                    "general": {}
                },
                "default_image_id": "db12c199-d0b5-47d3-8a97-e95eeaeae615",
                "user_keypair_id": "doc-keypair",
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "namenode",
                            "jobtracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-master-001",
                                "instance_id": "b366f88c-bf7d-4371-a046-96179ded4c83",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "ea34d320-09d7-4dc1-acbf-75b57cec81c9"
                    },
                    {
                        "count": 3,
                        "name": "worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-worker-001",
                                "instance_id": "f9fcd132-0534-4023-b4f6-9e10e2156299",
                                "volumes": []
                            },
                            {
                                "instance_name": "doc-cluster-worker-002",
                                "instance_id": "ce486914-364c-456e-8b0e-322ad178ca9e",
                                "volumes": []
                            },
                            {
                                "instance_name": "doc-cluster-worker-003",
                                "instance_id": "21312b4f-82fd-4840-8ba6-1606c7a2a75a",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "6bbaba84-d936-4e76-9381-987d3568cf4c"
                    }
                ],
                "hadoop_version": "1.2.1",
                "id": "1bb1cced-765e-4a2b-a5b6-ac6bbb0bb798"
            }
        }

6.4 Scale Cluster
-----------------

.. http:put:: /v1.0/{tenant_id}/clusters/{cluster_id}

Normal Response Code: 202 (ACCEPTED)

Errors: none

Scale Cluster changing number of nodes in existing Node Groups or adding new Node Groups.

This operation returns updated Cluster.

**Example**:
    **request**

    .. sourcecode:: http

        PUT http://sahara/v1.0/775181/clusters/9d7g51a-8123-424e-sdsr3-eb222ec989b1

    .. sourcecode:: json

        {
            "resize_node_groups": [
                {
                    "count": 3,
                    "name": "worker"
                }
            ],

            "add_node_groups": [
                {
                    "count": 2,
                    "name": "big-worker",
                    "node_group_template_id": "daa50c37-b11b-4f3d-a586-e5dcd0a4110f"
                }
            ]
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster": {
                "status": "Validating",
                "info": {
                    "HDFS": {
                        "Web UI": "http://172.18.79.166:50070"
                    },
                    "MapReduce": {
                        "Web UI": "http://172.18.79.166:50030"
                    }
                },
                "description": "",
                "cluster_configs": {
                    "HDFS": {},
                    "MapReduce": {},
                    "general": {}
                },
                "default_image_id": "db12c199-d0b5-47d3-8a97-e95eeaeae615",
                "user_keypair_id": "doc-keypair",
                "cluster_template_id": "9426fcb7-4c61-457f-8138-ff3bcf8a55ae",
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "namenode",
                            "jobtracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-master-001",
                                "internal_ip": "10.155.0.85",
                                "instance_id": "c6ddd972-e9a3-4c3d-a572-ee5f689dbd54",
                                "management_ip": "172.18.79.166",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "e66689e0-4486-4634-ac92-66ac74a86ba6"
                    },
                    {
                        "count": 3,
                        "name": "worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-worker-001",
                                "internal_ip": "10.155.0.86",
                                "instance_id": "4652aec1-0086-41fc-9d52-e0a22497fa36",
                                "management_ip": "172.18.79.165",
                                "volumes": []
                            },
                            {
                                "instance_name": "doc-cluster-worker-002",
                                "internal_ip": "10.155.0.84",
                                "instance_id": "42609367-20b9-4211-9fbb-bc20348d43e5",
                                "management_ip": "172.18.79.164",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "24ed6654-7160-4705-85f3-9e28310842af"
                    },
                    {
                        "count": 2,
                        "name": "big-worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "volumes_size": 10,
                        "node_processes": [
                            "datanode",
                            "tasktracker"
                        ],
                        "flavor_id": "42",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {},
                            "MapReduce": {}
                        },
                        "instances": [
                            {
                                "instance_name": "doc-cluster-big-worker-001",
                                "internal_ip": "10.155.0.88",
                                "instance_id": "747ba11f-ccc8-4119-ac46-77161f0bf12c",
                                "management_ip": "172.18.79.169",
                                "volumes": []
                            },
                            {
                                "instance_name": "doc-cluster-big-worker-002",
                                "internal_ip": "10.155.0.89",
                                "instance_id": "2b0431aa-0707-4e9f-96bb-8f4493e6e340",
                                "management_ip": "172.18.79.160",
                                "volumes": []
                            }
                        ],
                        "node_group_template_id": "24ed6654-7160-4705-85f3-9e28310842af"
                    }
                ],
                "hadoop_version": "1.2.1",
                "id": "e8918684-0941-4637-8238-6fc03a9ba043",
                "name": "doc-cluster"
            }
        }

6.5 Terminate Cluster
---------------------

.. http:delete:: /v1.0/{tenant_id}/clusters/{cluster_id}

Normal Response Code: 204 (NO CONTENT)

Errors: none

Terminate existing cluster.

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara/v1.0/775181/clusters/9d7g51a-8123-424e-sdsr3-eb222ec989b1

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json
