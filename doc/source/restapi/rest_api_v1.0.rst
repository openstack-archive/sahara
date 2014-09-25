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
                    "description": "This plugin provides an ability to launch vanilla Apache Hadoop cluster without any management consoles. Also it can deploy Oozie and Hive",
                    "versions": [
                        "1.2.1",
                        "2.3.0",
                        "2.4.1"
                    ],
                    "name": "vanilla",
                    "title": "Vanilla Apache Hadoop"
                },
                {
                    "description": "The Hortonworks OpenStack plugin works with project Sahara to automate the deployment of the Hortonworks data platform on OpenStack based public & private clouds",
                    "versions": [
                        "1.3.2",
                        "2.0.6"
                    ],
                    "name": "hdp",
                    "title": "Hortonworks Data Platform"
                },
                {
                    "description": "This plugin provides an ability to launch Spark on Hadoop CDH cluster without any management consoles.",
                    "versions": [
                        "1.0.0",
                        "0.9.1"
                    ],
                    "name": "spark",
                    "title": "Apache Spark"
                },
                {
                    "description": "This plugin provides an ability to launch CDH clusters with Cloudera Manager management console.",
                    "versions": [
                        "5"
                    ],
                    "name": "cdh",
                    "title": "Cloudera Plugin"
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
                "description": "This plugin provides an ability to launch vanilla Apache Hadoop cluster without any management consoles. Also it can deploy Oozie and Hive",
                "name": "vanilla",
                "versions": [
                    "1.2.1",
                    "2.3.0",
                    "2.4.1"
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

        GET http://sahara/v1.0/775181/plugins/vanilla/2.4.1

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
                    "JobFlow": [
                        "oozie"
                    ],
                    "Hadoop": [],
                    "YARN": [
                        "resourcemanager",
                        "nodemanager"
                    ],
                    "MapReduce": [
                        "historyserver"
                    ]
                },
                "description": "This plugin provides an ability to launch vanilla Apache Hadoop cluster without any management consoles. Also it can deploy Oozie and Hive",
                "versions": [
                    "1.2.1",
                    "2.3.0",
                    "2.4.1"
                ],
                "required_image_tags": [
                    "vanilla",
                    "2.4.1"
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
                    {
                        "default_value": 1024,
                        "name": "NodeManager Heap Size",
                        "config_values": null,
                        "priority": 1,
                        "config_type": "int",
                        "applicable_target": "YARN",
                        "is_optional": false,
                        "scope": "node",
                        "description": null
                    },
                    {
                        "default_value": true,
                        "name": "Enable Swift",
                        "config_values": null,
                        "priority": 1,
                        "config_type": "bool",
                        "applicable_target": "general",
                        "is_optional": false,
                        "scope": "cluster",
                        "description": null
                    },
                    {
                        "default_value": true,
                        "name": "Enable MySQL",
                        "config_values": null,
                        "priority": 1,
                        "config_type": "bool",
                        "applicable_target": "general",
                        "is_optional": true,
                        "scope": "cluster",
                        "description": null
                    }
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

This operation returns Sahara's JSON representation of a cluster template created
from the posted configuration.

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
                        "security_groups": [],
                        "auto_security_group": False,
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
                        "security_groups": [],
                        "auto_security_group": False,
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
                    "username": "ubuntu",
                    "updated": "2014-08-26T07:29:36Z",
                    "OS-EXT-IMG-SIZE:size": 965476352,
                    "name": "ubuntu-sahara-vanilla-2.4.1",
                    "created": "2014-08-26T07:16:40Z",
                    "tags": [
                        "2.4.1",
                        "vanilla"
                    ],
                    "minDisk": 0,
                    "progress": 100,
                    "minRam": 0,
                    "metadata": {
                        "_sahara_username": "ubuntu",
                        "_sahara_tag_2.4.1": "True",
                        "_sahara_description": "Ubuntu image for Hadoop 2.4.1",
                        "_sahara_tag_vanilla": "True"
                    },
                    "id": "5880a275-df8e-49cc-991a-e3a0b1fcf8ea",
                    "description": "Ubuntu image for Hadoop 2.4.1"
                },
                {
                    "status": "ACTIVE",
                    "username": "ubuntu",
                    "updated": "2014-08-08T12:45:37Z",
                    "OS-EXT-IMG-SIZE:size": 962658304,
                    "name": "sahara-icehouse-vanilla-1.2.1-ubuntu-13.10",
                    "created": "2014-08-08T12:43:47Z",
                    "tags": [
                        "vanilla",
                        "1.2.1"
                    ],
                    "minDisk": 0,
                    "progress": 100,
                    "minRam": 0,
                    "metadata": {
                        "_sahara_username": "ubuntu",
                        "_sahara_tag_vanilla": "True",
                        "_sahara_tag_1.2.1": "True"
                    },
                    "id": "d62ad147-5c10-418c-a21a-3a6597044f29",
                    "description": null
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

        GET http://sahara/v1.0/775181/images?tags=2.4.1

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "images": [
                {
                    "status": "ACTIVE",
                    "username": "ubuntu",
                    "updated": "2014-08-26T07:29:36Z",
                    "OS-EXT-IMG-SIZE:size": 965476352,
                    "name": "ubuntu-sahara-vanilla-2.4.1",
                    "created": "2014-08-26T07:16:40Z",
                    "tags": [
                        "2.4.1",
                        "vanilla"
                    ],
                    "minDisk": 0,
                    "progress": 100,
                    "minRam": 0,
                    "metadata": {
                        "_sahara_username": "ubuntu",
                        "_sahara_tag_2.4.1": "True",
                        "_sahara_description": "Ubuntu image for Hadoop 2.4.1",
                        "_sahara_tag_vanilla": "True"
                    },
                    "id": "5880a275-df8e-49cc-991a-e3a0b1fcf8ea",
                    "description": "Ubuntu image for Hadoop 2.4.1"
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

        GET http://sahara/v1.0/775181/images/d62ad147-5c10-418c-a21a-3a6597044f29

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "image": {
                "status": "ACTIVE",
                "username": "ubuntu",
                "updated": "2014-08-08T12:45:37Z",
                "OS-EXT-IMG-SIZE:size": 962658304,
                "name": "sahara-icehouse-vanilla-1.2.1-ubuntu-13.10",
                "created": "2014-08-08T12:43:47Z",
                "tags": [
                    "vanilla",
                    "1.2.1"
                ],
                "minDisk": 0,
                "progress": 100,
                "minRam": 0,
                "metadata": {
                    "_sahara_username": "ubuntu",
                    "_sahara_tag_vanilla": "True",
                    "_sahara_tag_1.2.1": "True"
                },
                "id": "d62ad147-5c10-418c-a21a-3a6597044f29",
                "description": null
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

        POST http://sahara/v1.0/775181/images/5880a275-df8e-49cc-991a-e3a0b1fcf8ea

    .. sourcecode:: json

        {
            "username": "ubuntu",
            "description": "Ubuntu image for Hadoop 2.4.1"
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "image": {
                "status": "ACTIVE",
                "username": "ubuntu",
                "updated": "2014-08-26T07:24:02Z",
                "OS-EXT-IMG-SIZE:size": 965476352,
                "name": "ubuntu-sahara-vanilla-2.4.1",
                "created": "2014-08-26T07:16:40Z",
                "tags": [],
                "minDisk": 0,
                "progress": 100,
                "minRam": 0,
                "metadata": {
                    "_sahara_username": "ubuntu",
                    "_sahara_description": "Ubuntu image for Hadoop 2.4.1"
                },
                "id": "5880a275-df8e-49cc-991a-e3a0b1fcf8ea",
                "description": "Ubuntu image for Hadoop 2.4.1"
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

        DELETE http://sahara/v1.0/775181/images/5880a275-df8e-49cc-991a-e3a0b1fcf8ea

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

        POST http://sahara/v1.0/775181/images/5880a275-df8e-49cc-991a-e3a0b1fcf8ea/tag

    .. sourcecode:: json

        {
            "tags": ["vanilla", "2.4.1", "some_other_tag"]
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "image": {
                "status": "ACTIVE",
                "username": "ubuntu",
                "updated": "2014-08-26T07:27:10Z",
                "OS-EXT-IMG-SIZE:size": 965476352,
                "name": "ubuntu-sahara-vanilla-2.4.1",
                "created": "2014-08-26T07:16:40Z",
                "tags": [
                    "some_other_tag",
                    "vanilla",
                    "2.4.1"
                ],
                "minDisk": 0,
                "progress": 100,
                "minRam": 0,
                "metadata": {
                    "_sahara_username": "ubuntu",
                    "_sahara_tag_some_other_tag": "True",
                    "_sahara_tag_vanilla": "True",
                    "_sahara_description": "Ubuntu image for Hadoop 2.4.1",
                    "_sahara_tag_2.4.1": "True"
                },
                "id": "5880a275-df8e-49cc-991a-e3a0b1fcf8ea",
                "description": "Ubuntu image for Hadoop 2.4.1"
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

        POST http://sahara/v1.0/775181/images/5880a275-df8e-49cc-991a-e3a0b1fcf8ea/untag

    .. sourcecode:: json

        {
            "tags": ["some_other_tag"]
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "image": {
                "status": "ACTIVE",
                "username": "ubuntu",
                "updated": "2014-08-26T07:29:36Z",
                "OS-EXT-IMG-SIZE:size": 965476352,
                "name": "ubuntu-sahara-vanilla-2.4.1",
                "created": "2014-08-26T07:16:40Z",
                "tags": [
                    "2.4.1",
                    "vanilla"
                ],
                "minDisk": 0,
                "progress": 100,
                "minRam": 0,
                "metadata": {
                    "_sahara_username": "ubuntu",
                    "_sahara_tag_2.4.1": "True",
                    "_sahara_description": "Ubuntu image for Hadoop 2.4.1",
                    "_sahara_tag_vanilla": "True"
                },
                "id": "5880a275-df8e-49cc-991a-e3a0b1fcf8ea",
                "description": "Ubuntu image for Hadoop 2.4.1"
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
                    "hadoop_version": "2.4.1",
                    "security_groups": null,
                    "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                    "name": "worker",
                    "updated_at": null,
                    "description": null,
                    "plugin_name": "vanilla",
                    "image_id": null,
                    "volumes_size": 0,
                    "id": "734551b4-0542-4bc1-b9bf-85f77d85c6f6",
                    "auto_security_group": null,
                    "volumes_per_node": 0,
                    "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                    "node_processes": [
                        "datanode",
                        "nodemanager"
                    ],
                    "created_at": "2014-09-02 23:02:29",
                    "node_configs": {
                        "HDFS": {
                            "DataNode Heap Size": 1024
                        },
                        "YARN": {
                            "NodeManager Heap Size": 2048
                        }
                    },
                    "volume_mount_prefix": "/volumes/disk",
                    "flavor_id": "3"
                },
                {
                    "hadoop_version": "2.4.1",
                    "security_groups": null,
                    "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                    "name": "master",
                    "updated_at": null,
                    "description": null,
                    "plugin_name": "vanilla",
                    "image_id": null,
                    "volumes_size": 0,
                    "id": "b900b4dc-d3ee-4341-99c3-ac078301f9d8",
                    "auto_security_group": null,
                    "volumes_per_node": 0,
                    "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                    "node_processes": [
                        "namenode",
                        "resourcemanager",
                        "oozie",
                        "historyserver"
                    ],
                    "created_at": "2014-09-02 23:01:33",
                    "node_configs": {},
                    "volume_mount_prefix": "/volumes/disk",
                    "flavor_id": "3"
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

        GET http://sahara/v1.0/775181/node-group-templates/b900b4dc-d3ee-4341-99c3-ac078301f9d8

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "node_group_template": {
                "hadoop_version": "2.4.1",
                "security_groups": null,
                "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                "name": "master",
                "updated_at": null,
                "description": null,
                "plugin_name": "vanilla",
                "image_id": null,
                "volumes_size": 0,
                "id": "b900b4dc-d3ee-4341-99c3-ac078301f9d8",
                "auto_security_group": null,
                "volumes_per_node": 0,
                "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                "node_processes": [
                    "namenode",
                    "resourcemanager",
                    "oozie",
                    "historyserver"
                ],
                "created_at": "2014-09-02 23:01:33",
                "node_configs": {},
                "volume_mount_prefix": "/volumes/disk",
                "flavor_id": "3"
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
            "hadoop_version": "2.4.1",
            "node_processes": [
                "namenode",
                "resourcemanager",
                "oozie",
                "historyserver"
            ],
            "name": "master",
            "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
            "flavor_id": "3"
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
                "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                "created_at": "2014-08-26 08:14:46.119233",
                "plugin_name": "vanilla",
                "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                "volumes_size": 0,
                "node_processes": [
                    "namenode",
                    "resourcemanager",
                    "oozie",
                    "historyserver"
                ],
                "flavor_id": "3",
                "volumes_per_node": 0,
                "auto_security_group": null,
                "hadoop_version": "2.4.1",
                "id": "b900b4dc-d3ee-4341-99c3-ac078301f9d8",
                "security_groups": null
            }
        }

**Example with configurations**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/node-group-templates

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "2.4.1",
            "node_processes": [
                "datanode",
                "nodemanager"
            ],
            "name": "worker",
            "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
            "flavor_id": "3",
            "node_configs": {
                "HDFS": {
                    "DataNode Heap Size": 1024
                },
                "YARN": {
                    "NodeManager Heap Size": 2048
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
                "tenant_id": "28a4d0e49b024dc0875ed6a862b129f0",
                "created_at": "2014-08-26 08:23:06.740466",
                "plugin_name": "vanilla",
                "floating_ip_pool": "cdeaa720-5517-4878-860e-71a1926744aa",
                "volumes_size": 0,
                "node_processes": [
                    "datanode",
                    "nodemanager"
                ],
                "flavor_id": "3",
                "volumes_per_node": 0,
                "security_groups": [],
                "auto_security_group": False,
                "node_configs": {
                    "HDFS": {
                        "DataNode Heap Size": 1024
                    },
                    "YARN": {
                        "NodeManager Heap Size": 2048
                    }
                },
                "hadoop_version": "2.4.1",
                "id": "3b975888-42d4-43d3-be70-8e4401e3cb65",
                "security_groups": null
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
                    "hadoop_version": "2.4.1",
                    "default_image_id": null,
                    "name": "cluster-template",
                    "updated_at": null,
                    "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                    "plugin_name": "vanilla",
                    "anti_affinity": [],
                    "description": null,
                    "id": "1beae95b-fd20-47c0-a745-5125dccbd560",
                    "node_groups": [
                        {
                            "security_groups": null,
                            "name": "master",
                            "updated_at": null,
                            "count": 1,
                            "node_processes": [
                                "namenode",
                                "resourcemanager",
                                "oozie",
                                "historyserver"
                            ],
                            "node_configs": {},
                            "volumes_size": 0,
                            "auto_security_group": null,
                            "volumes_per_node": 0,
                            "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                            "node_group_template_id": "b900b4dc-d3ee-4341-99c3-ac078301f9d8",
                            "created_at": "2014-09-02 23:05:23",
                            "image_id": null,
                            "volume_mount_prefix": "/volumes/disk",
                            "flavor_id": "3"
                        },
                        {
                            "security_groups": null,
                            "name": "worker",
                            "updated_at": null,
                            "count": 3,
                            "node_processes": [
                                "datanode",
                                "nodemanager"
                            ],
                            "node_configs": {
                                "HDFS": {
                                    "DataNode Heap Size": 1024
                                },
                                "YARN": {
                                    "NodeManager Heap Size": 2048
                                }
                            },
                            "volumes_size": 0,
                            "auto_security_group": null,
                            "volumes_per_node": 0,
                            "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                            "node_group_template_id": "734551b4-0542-4bc1-b9bf-85f77d85c6f6",
                            "created_at": "2014-09-02 23:05:23",
                            "image_id": null,
                            "volume_mount_prefix": "/volumes/disk",
                            "flavor_id": "3"
                        }
                    ],
                    "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
                    "created_at": "2014-09-02 23:05:23",
                    "cluster_configs": {}
                },
                {
                    "hadoop_version": "2.4.1",
                    "default_image_id": null,
                    "name": "cluster-template-3",
                    "updated_at": null,
                    "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                    "plugin_name": "vanilla",
                    "anti_affinity": [],
                    "description": null,
                    "id": "3d5bdb90-c8c5-4100-81b8-81d23cecaab2",
                    "node_groups": [
                        {
                            "security_groups": null,
                            "name": "master",
                            "updated_at": null,
                            "count": 1,
                            "node_processes": [
                                "namenode",
                                "resourcemanager",
                                "oozie",
                                "historyserver"
                            ],
                            "node_configs": {},
                            "volumes_size": 0,
                            "auto_security_group": null,
                            "volumes_per_node": 0,
                            "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                            "node_group_template_id": null,
                            "created_at": "2014-09-02 23:06:39",
                            "image_id": null,
                            "volume_mount_prefix": "/volumes/disk",
                            "flavor_id": "3"
                        },
                        {
                            "security_groups": null,
                            "name": "worker",
                            "updated_at": null,
                            "count": 3,
                            "node_processes": [
                                "datanode",
                                "nodemanager"
                            ],
                            "node_configs": {
                                "HDFS": {
                                    "DataNode Heap Size": 1024
                                },
                                "YARN": {
                                    "NodeManager Heap Size": 2048
                                }
                            },
                            "volumes_size": 0,
                            "auto_security_group": null,
                            "volumes_per_node": 0,
                            "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                            "node_group_template_id": null,
                            "created_at": "2014-09-02 23:06:38",
                            "image_id": null,
                            "volume_mount_prefix": "/volumes/disk",
                            "flavor_id": "3"
                        }
                    ],
                    "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
                    "created_at": "2014-09-02 23:06:38",
                    "cluster_configs": {
                        "HDFS": {
                            "dfs.replication": 3
                        },
                        "general": {
                            "Enable Swift": true,
                            "Enable MySQL": true
                        }
                    }
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

        GET http://sahara/v1.0/775181/cluster-templates/1beae95b-fd20-47c0-a745-5125dccbd560

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster_template": {
                "hadoop_version": "2.4.1",
                "default_image_id": null,
                "name": "cluster-template",
                "updated_at": null,
                "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "description": null,
                "id": "1beae95b-fd20-47c0-a745-5125dccbd560",
                "node_groups": [
                    {
                        "security_groups": null,
                        "name": "master",
                        "updated_at": null,
                        "count": 1,
                        "node_processes": [
                            "namenode",
                            "resourcemanager",
                            "oozie",
                            "historyserver"
                        ],
                        "node_configs": {},
                        "volumes_size": 0,
                        "auto_security_group": null,
                        "volumes_per_node": 0,
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "node_group_template_id": "b900b4dc-d3ee-4341-99c3-ac078301f9d8",
                        "created_at": "2014-09-02 23:05:23",
                        "image_id": null,
                        "volume_mount_prefix": "/volumes/disk",
                        "flavor_id": "3"
                    },
                    {
                        "security_groups": null,
                        "name": "worker",
                        "updated_at": null,
                        "count": 3,
                        "node_processes": [
                            "datanode",
                            "nodemanager"
                        ],
                        "node_configs": {
                            "HDFS": {
                                "DataNode Heap Size": 1024
                            },
                            "YARN": {
                                "NodeManager Heap Size": 2048
                            }
                        },
                        "volumes_size": 0,
                        "auto_security_group": null,
                        "volumes_per_node": 0,
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "node_group_template_id": "734551b4-0542-4bc1-b9bf-85f77d85c6f6",
                        "created_at": "2014-09-02 23:05:23",
                        "image_id": null,
                        "volume_mount_prefix": "/volumes/disk",
                        "flavor_id": "3"
                    }
                ],
                "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
                "created_at": "2014-09-02 23:05:23",
                "cluster_configs": {}
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
            "hadoop_version": "2.4.1",
            "node_groups": [
                {
                    "name": "worker",
                    "count": 3,
                    "node_group_template_id": "3b975888-42d4-43d3-be70-8e4401e3cb65"
                },
                {
                    "name": "master",
                    "count": 1,
                    "node_group_template_id": "208f2d53-69c3-48c3-9830-986db4c29c95"
                }
            ],
            "name": "cluster-template",
            "neutron_management_network": "0b001fb7-b172-43f0-8c99-444672fd0513",
            "cluster_configs": {}
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster_template": {
                "neutron_management_network": "0b001fb7-b172-43f0-8c99-444672fd0513",
                "description": null,
                "cluster_configs": {},
                "created_at": "2014-08-28 20:00:40",
                "default_image_id": null,
                "updated_at": null,
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "tenant_id": "28a4d0e49b024dc0875ed6a862b129f0",
                "node_groups": [
                    {
                        "count": 3,
                        "name": "worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "auto_security_group": null,
                        "created_at": "2014-08-28 20:00:40",
                        "updated_at": null,
                        "floating_ip_pool": "cdeaa720-5517-4878-860e-71a1926744aa",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_processes": [
                            "datanode",
                            "nodemanager"
                        ],
                        "node_group_template_id": "3b975888-42d4-43d3-be70-8e4401e3cb65",
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {
                                "DataNode Heap Size": 1024
                            },
                            "YARN": {
                                "NodeManager Heap Size": 2048
                            }
                        },
                        "security_groups": null,
                        "flavor_id": "3"
                    },
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "auto_security_group": null,
                        "created_at": "2014-08-28 20:00:40",
                        "updated_at": null,
                        "floating_ip_pool": "cdeaa720-5517-4878-860e-71a1926744aa",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_processes": [
                            "namenode",
                            "resourcemanager",
                            "oozie",
                            "historyserver"
                        ],
                        "node_group_template_id": "208f2d53-69c3-48c3-9830-986db4c29c95",
                        "volumes_per_node": 0,
                        "node_configs": {},
                        "security_groups": null,
                        "flavor_id": "3"
                    }
                ],
                "hadoop_version": "2.4.1",
                "id": "1beae95b-fd20-47c0-a745-5125dccbd560",
                "name": "cluster-template"
            }
        }

**Example with configurations and no Node Group Templates**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/node-group-templates

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "2.4.1",
            "name": "cluster-template-3",
            "neutron_management_network": "0b001fb7-b172-43f0-8c99-444672fd0513",
            "cluster_configs": {
                "general": {
                  "Enable Swift": true,
                  "Enable MySQL": true
                },
                "HDFS": {
                    "dfs.replication": 3
                }
            },
            "node_groups": [
                {
                    "count": 3,
                    "name": "worker",
                    "floating_ip_pool": "cdeaa720-5517-4878-860e-71a1926744aa",
                    "node_processes": [
                        "datanode",
                        "nodemanager"
                    ],
                    "node_configs": {
                        "HDFS": {
                            "DataNode Heap Size": 1024
                        },
                        "YARN": {
                            "NodeManager Heap Size": 2048
                        }
                    },
                    "flavor_id": "3"
                },
                {
                    "count": 1,
                    "name": "master",
                    "floating_ip_pool": "cdeaa720-5517-4878-860e-71a1926744aa",
                    "node_processes": [
                        "namenode",
                        "resourcemanager",
                        "oozie",
                        "historyserver"
                    ],
                    "flavor_id": "3"
                }
            ]
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster_template": {
                "neutron_management_network": "0b001fb7-b172-43f0-8c99-444672fd0513",
                "description": null,
                "cluster_configs": {
                    "HDFS": {
                        "dfs.replication": 3
                    },
                    "general": {
                        "Enable MySQL": true,
                        "Enable Swift": true
                    }
                },
                "created_at": "2014-08-28 20:20:38",
                "default_image_id": null,
                "updated_at": null,
                "plugin_name": "vanilla",
                "anti_affinity": [],
                "tenant_id": "28a4d0e49b024dc0875ed6a862b129f0",
                "node_groups": [
                    {
                        "count": 3,
                        "name": "worker",
                        "volume_mount_prefix": "/volumes/disk",
                        "auto_security_group": null,
                        "created_at": "2014-08-28 20:20:38",
                        "updated_at": null,
                        "floating_ip_pool": "cdeaa720-5517-4878-860e-71a1926744aa",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_processes": [
                            "datanode",
                            "nodemanager"
                        ],
                        "node_group_template_id": null,
                        "volumes_per_node": 0,
                        "node_configs": {
                            "HDFS": {
                                "DataNode Heap Size": 1024
                            },
                            "YARN": {
                                "NodeManager Heap Size": 2048
                            }
                        },
                        "security_groups": null,
                        "flavor_id": "3"
                    },
                    {
                        "count": 1,
                        "name": "master",
                        "volume_mount_prefix": "/volumes/disk",
                        "auto_security_group": null,
                        "created_at": "2014-08-28 20:20:38",
                        "updated_at": null,
                        "floating_ip_pool": "cdeaa720-5517-4878-860e-71a1926744aa",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_processes": [
                            "namenode",
                            "resourcemanager",
                            "oozie",
                            "historyserver"
                        ],
                        "node_group_template_id": null,
                        "volumes_per_node": 0,
                        "node_configs": {},
                        "security_groups": null,
                        "flavor_id": "3"
                    }
                ],
                "hadoop_version": "2.4.1",
                "id": "3a9c68e5-47f0-479b-9ee9-f86ccb0be68c",
                "name": "cluster-template-3"
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

        DELETE http://sahara/v1.0/775181/cluster-templates/3a9c68e5-47f0-479b-9ee9-f86ccb0be68c

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
                    "status": "Active",
                    "info": {
                        "HDFS": {
                            "NameNode": "hdfs://doc-cluster-master-001:9000",
                            "Web UI": "http://172.18.168.227:50070"
                        },
                        "JobFlow": {
                            "Oozie": "http://172.18.168.227:11000"
                        },
                        "MapReduce JobHistory Server": {
                            "Web UI": "http://172.18.168.227:19888"
                        },
                        "YARN": {
                            "Web UI": "http://172.18.168.227:8088"
                        }
                    },
                    "cluster_template_id": "1beae95b-fd20-47c0-a745-5125dccbd560",
                    "is_transient": false,
                    "description": null,
                    "cluster_configs": {},
                    "created_at": "2014-09-02 23:13:50",
                    "default_image_id": "be23ce84-68cb-490a-b50e-e4f3e340d5d7",
                    "user_keypair_id": "doc-keypair",
                    "updated_at": "2014-09-02 23:17:22",
                    "plugin_name": "vanilla",
                    "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
                    "anti_affinity": [],
                    "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                    "node_groups": [
                        {
                            "count": 1,
                            "name": "master",
                            "auto_security_group": null,
                            "instances": [
                                {
                                    "instance_name": "doc-cluster-master-001",
                                    "created_at": "2014-09-02 23:13:53",
                                    "updated_at": "2014-09-02 23:14:27",
                                    "instance_id": "59dd622c-787d-4bb8-98a2-33887dfc5b41",
                                    "management_ip": "172.18.168.227",
                                    "volumes": [],
                                    "internal_ip": "10.50.0.55",
                                    "id": "a01cd5a1-5c4e-419e-9718-c8e839995150"
                                }
                            ],
                            "volume_mount_prefix": "/volumes/disk",
                            "created_at": "2014-09-02 23:13:50",
                            "updated_at": "2014-09-02 23:13:53",
                            "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                            "image_id": null,
                            "volumes_size": 0,
                            "node_configs": {},
                            "node_group_template_id": "b900b4dc-d3ee-4341-99c3-ac078301f9d8",
                            "volumes_per_node": 0,
                            "node_processes": [
                                "namenode",
                                "resourcemanager",
                                "oozie",
                                "historyserver"
                            ],
                            "security_groups": null,
                            "flavor_id": "3"
                        },
                        {
                            "count": 3,
                            "name": "worker",
                            "auto_security_group": null,
                            "instances": [
                                {
                                    "instance_name": "doc-cluster-worker-001",
                                    "created_at": "2014-09-02 23:13:52",
                                    "updated_at": "2014-09-02 23:14:27",
                                    "instance_id": "be59bf7b-5b63-4e63-ba13-fbfd94078885",
                                    "management_ip": "172.18.168.226",
                                    "volumes": [],
                                    "internal_ip": "10.50.0.53",
                                    "id": "b4e9d4ad-e421-4bf1-8b4d-756154f7396a"
                                },
                                {
                                    "instance_name": "doc-cluster-worker-002",
                                    "created_at": "2014-09-02 23:13:52",
                                    "updated_at": "2014-09-02 23:14:28",
                                    "instance_id": "19c55dea-2a03-41c6-adba-2512a38bc708",
                                    "management_ip": "172.18.168.228",
                                    "volumes": [],
                                    "internal_ip": "10.50.0.56",
                                    "id": "e1cb99d6-bce5-4df6-8725-522224154119"
                                },
                                {
                                    "instance_name": "doc-cluster-worker-003",
                                    "created_at": "2014-09-02 23:13:53",
                                    "updated_at": "2014-09-02 23:14:27",
                                    "instance_id": "25ee1e5e-1839-4919-be85-70733bf0238b",
                                    "management_ip": "172.18.168.225",
                                    "volumes": [],
                                    "internal_ip": "10.50.0.54",
                                    "id": "1bdbc0bc-bd15-481f-9f64-a6c79449afe4"
                                }
                            ],
                            "volume_mount_prefix": "/volumes/disk",
                            "created_at": "2014-09-02 23:13:50",
                            "updated_at": "2014-09-02 23:13:53",
                            "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                            "image_id": null,
                            "volumes_size": 0,
                            "node_configs": {
                                "HDFS": {
                                    "DataNode Heap Size": 1024
                                },
                                "YARN": {
                                    "NodeManager Heap Size": 2048
                                }
                            },
                            "node_group_template_id": "734551b4-0542-4bc1-b9bf-85f77d85c6f6",
                            "volumes_per_node": 0,
                            "node_processes": [
                                "datanode",
                                "nodemanager"
                            ],
                            "security_groups": null,
                            "flavor_id": "3"
                        }
                    ],
                    "management_public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDcKdaU6FpUV0qyDkOazP6ffXwy4Ydc6ZKArSV+Oo8F0Ldo2WM6cGkoh38uDEWiSXPVv+s+Mpnjn40DtkZVm3nFM9gmk+05a5pXNbch/PPDJtTOaVPwDCCij/vPFhqsA42RRTRw9DgF5rwJEz25kFoblaQ7vt5NouH14IyTVxJdU/s5oKPB6f3C1otQ70ZJXtd4uDLswbFR9nsKK/hy0WOLpcdefovgtWU63nz0+WO1HRfAgZVUV51p/p6plHIoRqaJiddX5MCykopVdFfoIKp4ERw0QwHEleu6tPsjqJtS7pWpNmKsiLnzu7ZAtWDnEVx63EzxKIKOJFll5Pvc9Buh Generated by Sahara\n",
                    "status_description": "",
                    "hadoop_version": "2.4.1",
                    "id": "fa57eed8-ee5e-4f9a-b365-7ca92e389ba0",
                    "trust_id": null,
                    "name": "doc-cluster"
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

        GET http://sahara/v1.0/775181/clusters/fa57eed8-ee5e-4f9a-b365-7ca92e389ba0

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "cluster": {
                "status": "Active",
                "info": {
                    "HDFS": {
                        "NameNode": "hdfs://doc-cluster-master-001:9000",
                        "Web UI": "http://172.18.168.227:50070"
                    },
                    "JobFlow": {
                        "Oozie": "http://172.18.168.227:11000"
                    },
                    "MapReduce JobHistory Server": {
                        "Web UI": "http://172.18.168.227:19888"
                    },
                    "YARN": {
                        "Web UI": "http://172.18.168.227:8088"
                    }
                },
                "cluster_template_id": "1beae95b-fd20-47c0-a745-5125dccbd560",
                "is_transient": false,
                "description": null,
                "cluster_configs": {},
                "created_at": "2014-09-02 23:13:50",
                "default_image_id": "be23ce84-68cb-490a-b50e-e4f3e340d5d7",
                "user_keypair_id": "doc-keypair",
                "updated_at": "2014-09-02 23:17:22",
                "plugin_name": "vanilla",
                "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
                "anti_affinity": [],
                "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "auto_security_group": null,
                        "instances": [
                            {
                                "instance_name": "doc-cluster-master-001",
                                "created_at": "2014-09-02 23:13:53",
                                "updated_at": "2014-09-02 23:14:27",
                                "instance_id": "59dd622c-787d-4bb8-98a2-33887dfc5b41",
                                "management_ip": "172.18.168.227",
                                "volumes": [],
                                "internal_ip": "10.50.0.55",
                                "id": "a01cd5a1-5c4e-419e-9718-c8e839995150"
                            }
                        ],
                        "volume_mount_prefix": "/volumes/disk",
                        "created_at": "2014-09-02 23:13:50",
                        "updated_at": "2014-09-02 23:13:53",
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {},
                        "node_group_template_id": "b900b4dc-d3ee-4341-99c3-ac078301f9d8",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "namenode",
                            "resourcemanager",
                            "oozie",
                            "historyserver"
                        ],
                        "security_groups": null,
                        "flavor_id": "3"
                    },
                    {
                        "count": 3,
                        "name": "worker",
                        "auto_security_group": null,
                        "instances": [
                            {
                                "instance_name": "doc-cluster-worker-001",
                                "created_at": "2014-09-02 23:13:52",
                                "updated_at": "2014-09-02 23:14:27",
                                "instance_id": "be59bf7b-5b63-4e63-ba13-fbfd94078885",
                                "management_ip": "172.18.168.226",
                                "volumes": [],
                                "internal_ip": "10.50.0.53",
                                "id": "b4e9d4ad-e421-4bf1-8b4d-756154f7396a"
                            },
                            {
                                "instance_name": "doc-cluster-worker-002",
                                "created_at": "2014-09-02 23:13:52",
                                "updated_at": "2014-09-02 23:14:28",
                                "instance_id": "19c55dea-2a03-41c6-adba-2512a38bc708",
                                "management_ip": "172.18.168.228",
                                "volumes": [],
                                "internal_ip": "10.50.0.56",
                                "id": "e1cb99d6-bce5-4df6-8725-522224154119"
                            },
                            {
                                "instance_name": "doc-cluster-worker-003",
                                "created_at": "2014-09-02 23:13:53",
                                "updated_at": "2014-09-02 23:14:27",
                                "instance_id": "25ee1e5e-1839-4919-be85-70733bf0238b",
                                "management_ip": "172.18.168.225",
                                "volumes": [],
                                "internal_ip": "10.50.0.54",
                                "id": "1bdbc0bc-bd15-481f-9f64-a6c79449afe4"
                            }
                        ],
                        "volume_mount_prefix": "/volumes/disk",
                        "created_at": "2014-09-02 23:13:50",
                        "updated_at": "2014-09-02 23:13:53",
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {
                            "HDFS": {
                                "DataNode Heap Size": 1024
                            },
                            "YARN": {
                                "NodeManager Heap Size": 2048
                            }
                        },
                        "node_group_template_id": "734551b4-0542-4bc1-b9bf-85f77d85c6f6",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "nodemanager"
                        ],
                        "security_groups": null,
                        "flavor_id": "3"
                    }
                ],
                "management_public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDcKdaU6FpUV0qyDkOazP6ffXwy4Ydc6ZKArSV+Oo8F0Ldo2WM6cGkoh38uDEWiSXPVv+s+Mpnjn40DtkZVm3nFM9gmk+05a5pXNbch/PPDJtTOaVPwDCCij/vPFhqsA42RRTRw9DgF5rwJEz25kFoblaQ7vt5NouH14IyTVxJdU/s5oKPB6f3C1otQ70ZJXtd4uDLswbFR9nsKK/hy0WOLpcdefovgtWU63nz0+WO1HRfAgZVUV51p/p6plHIoRqaJiddX5MCykopVdFfoIKp4ERw0QwHEleu6tPsjqJtS7pWpNmKsiLnzu7ZAtWDnEVx63EzxKIKOJFll5Pvc9Buh Generated by Sahara\n",
                "status_description": "",
                "hadoop_version": "2.4.1",
                "id": "fa57eed8-ee5e-4f9a-b365-7ca92e389ba0",
                "trust_id": null,
                "name": "doc-cluster"
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
            "hadoop_version": "2.4.1",
            "cluster_template_id": "1beae95b-fd20-47c0-a745-5125dccbd560",
            "default_image_id": "be23ce84-68cb-490a-b50e-e4f3e340d5d7",
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
                "status": "Validating",
                "info": {},
                "cluster_template_id": "1beae95b-fd20-47c0-a745-5125dccbd560",
                "is_transient": false,
                "description": null,
                "cluster_configs": {},
                "created_at": "2014-09-02 23:40:36",
                "default_image_id": "be23ce84-68cb-490a-b50e-e4f3e340d5d7",
                "user_keypair_id": "doc-keypair",
                "updated_at": "2014-09-02 23:40:36.265920",
                "plugin_name": "vanilla",
                "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
                "anti_affinity": [],
                "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "instances": [],
                        "volume_mount_prefix": "/volumes/disk",
                        "created_at": "2014-09-02 23:40:36",
                        "updated_at": null,
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {},
                        "node_group_template_id": "b900b4dc-d3ee-4341-99c3-ac078301f9d8",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "namenode",
                            "resourcemanager",
                            "oozie",
                            "historyserver"
                        ],
                        "security_groups": null,
                        "auto_security_group": null,
                        "flavor_id": "3"
                    },
                    {
                        "count": 3,
                        "name": "worker",
                        "instances": [],
                        "volume_mount_prefix": "/volumes/disk",
                        "auto_security_group": null,
                        "created_at": "2014-09-02 23:40:36",
                        "updated_at": null,
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {
                            "HDFS": {
                                "DataNode Heap Size": 1024
                            },
                            "YARN": {
                                "NodeManager Heap Size": 2048
                            }
                        },
                        "node_group_template_id": "734551b4-0542-4bc1-b9bf-85f77d85c6f6",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "nodemanager"
                        ],
                        "security_groups": null,
                        "flavor_id": "3"
                    }
                ],
                "management_public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDBgbVVyS6gQZA28TooEqzUKvjFw71CXo393Q99jFsv1DfvrcbcYnpX/dPC9psMyg/nYb6B3/7aNpWXUq7/1zIf1StaPV+ZrpzT4UHVlwhmaYYNx4usoFxJfY8vdEOe9t8RO6UQPlVhbD1XJqizhUx4RTUfiDKhzbP/FwoYqKFtBoTxRYpPzg/lCLc0L4jYVjVEuc4Px+mCoPOse8Jgho26ES1m/45kt77ayYC08J8TKjSe+ikA9W3a9OhkOhiz7mZHZq4T5ix61PD72x83aceufR++vDWZc2WRNOXNRD810P5UkXqhdUBOL+lHeIM/97zrhvtmf6jzcQ+KQwUohHUX Generated by Sahara\n",
                "status_description": "",
                "hadoop_version": "2.4.1",
                "id": "c8c3fee5-075a-4969-875b-9a00bb9c7c6c",
                "trust_id": null,
                "name": "doc-cluster"
            }
        }

**Example Cluster creation from Node Groups and with configurations**:
    **request**

    .. sourcecode:: http

        POST http://sahara/v1.0/775181/clusters

    .. sourcecode:: json

        {
            "plugin_name": "vanilla",
            "hadoop_version": "2.4.1",
            "name": "doc-cluster",
            "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
            "default_image_id": "be23ce84-68cb-490a-b50e-e4f3e340d5d7",
            "cluster_configs": {
                "general": {
                  "Enable Swift": true,
                  "Enable MySQL": true
                },
                "HDFS": {
                    "dfs.replication": 3
                }
            },
            "node_groups": [
                {
                    "count": 3,
                    "name": "worker",
                    "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                    "node_processes": [
                        "datanode",
                        "nodemanager"
                    ],
                    "node_configs": {
                        "HDFS": {
                            "DataNode Heap Size": 1024
                        },
                        "YARN": {
                            "NodeManager Heap Size": 2048
                        }
                    },
                    "flavor_id": "3"
                },
                {
                    "count": 1,
                    "name": "master",
                    "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                    "node_processes": [
                        "namenode",
                        "resourcemanager",
                        "oozie",
                        "historyserver"
                    ],
                    "flavor_id": "3"
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
                "status": "Waiting",
                "info": {},
                "cluster_template_id": null,
                "is_transient": false,
                "description": null,
                "cluster_configs": {
                    "HDFS": {
                        "dfs.replication": 3
                    },
                    "general": {
                        "Enable MySQL": true,
                        "Enable Swift": true
                    }
                },
                "created_at": "2014-09-02 23:34:09",
                "default_image_id": "be23ce84-68cb-490a-b50e-e4f3e340d5d7",
                "user_keypair_id": null,
                "updated_at": "2014-09-02 23:34:13",
                "plugin_name": "vanilla",
                "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
                "anti_affinity": [],
                "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                "node_groups": [
                    {
                        "count": 1,
                        "name": "master",
                        "auto_security_group": null,
                        "instances": [
                            {
                                "instance_name": "cluster-template-3-master-001",
                                "created_at": "2014-09-02 23:34:13",
                                "updated_at": "2014-09-02 23:34:56",
                                "instance_id": "c7d17c4f-56fc-46a4-bcd1-76ec3d459d82",
                                "management_ip": "172.18.168.233",
                                "volumes": [],
                                "internal_ip": "10.50.0.59",
                                "id": "47aac1fc-11e2-4f89-b699-69ede345379b"
                            }
                        ],
                        "volume_mount_prefix": "/volumes/disk",
                        "created_at": "2014-09-02 23:34:09",
                        "updated_at": "2014-09-02 23:34:13",
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {},
                        "node_group_template_id": null,
                        "volumes_per_node": 0,
                        "node_processes": [
                            "namenode",
                            "resourcemanager",
                            "oozie",
                            "historyserver"
                        ],
                        "security_groups": null,
                        "flavor_id": "3"
                    },
                    {
                        "count": 3,
                        "name": "worker",
                        "auto_security_group": null,
                        "instances": [
                            {
                                "instance_name": "cluster-template-3-worker-001",
                                "created_at": "2014-09-02 23:34:11",
                                "updated_at": "2014-09-02 23:34:55",
                                "instance_id": "3e2a0cc1-fd25-42c0-885d-efffb11f56e3",
                                "management_ip": "172.18.168.232",
                                "volumes": [],
                                "internal_ip": "10.50.0.57",
                                "id": "e6b41b36-dfa8-49f6-ab19-a3796d510014"
                            },
                            {
                                "instance_name": "cluster-template-3-worker-002",
                                "created_at": "2014-09-02 23:34:12",
                                "updated_at": "2014-09-02 23:34:55",
                                "instance_id": "9e4d5f63-1424-4a8c-b830-b953fb674854",
                                "management_ip": "172.18.168.231",
                                "volumes": [],
                                "internal_ip": "10.50.0.60",
                                "id": "41d8808d-00f1-4887-8791-6ee990307095"
                            },
                            {
                                "instance_name": "cluster-template-3-worker-003",
                                "created_at": "2014-09-02 23:34:12",
                                "updated_at": "2014-09-02 23:34:56",
                                "instance_id": "4e7ecea4-1d2d-46ff-983f-ad3134601662",
                                "management_ip": "172.18.168.234",
                                "volumes": [],
                                "internal_ip": "10.50.0.58",
                                "id": "16d59d71-25fa-42eb-9a7a-f050224dd653"
                            }
                        ],
                        "volume_mount_prefix": "/volumes/disk",
                        "created_at": "2014-09-02 23:34:09",
                        "updated_at": "2014-09-02 23:34:12",
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {
                            "HDFS": {
                                "DataNode Heap Size": 1024
                            },
                            "YARN": {
                                "NodeManager Heap Size": 2048
                            }
                        },
                        "node_group_template_id": null,
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "nodemanager"
                        ],
                        "security_groups": null,
                        "flavor_id": "3"
                    }
                ],
                "management_public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwXKFhoOhyyKF3xtFcWv/TYw3lNS27X8AIwbBwUrwhvxYSLSqJO53YL7DRIIBGmzhCb+Y9+oPU50cgwvVvLH0ww7aBpAtsG3dMaEgv2xQzLwEVAy2TJOy+c1cxqaLfyrUlzx1mh4GXsqJlW2qjdDYPhCB1OSL2JIHACqhyZp/5YrgL84Etx6zcJeac+0x4Z3pCbjXzW7oQVRmHdhrcq/aMaX4qhWg3JxnVTflFg4jigGsWM2Cj2VNxdRNiZyyqwLO8YENi8hG6rEcuVWRU/v8N9DaqFj+JumPDQ5S6kBD6mk+5z1oISYUhW/6Syo4CTaHlrMcMoF9Mh9s86wLvW/o1 Generated by Sahara\n",
                "status_description": "",
                "hadoop_version": "2.4.1",
                "id": "b77e8def-a66d-4df8-bc9a-10a9a216fd60",
                "trust_id": null,
                "name": "doc-cluster"
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
                    "count": 4,
                    "name": "worker"
                }
            ],

            "add_node_groups": [
                {
                    "count": 2,
                    "name": "big-worker",
                    "node_group_template_id": "734551b4-0542-4bc1-b9bf-85f77d85c6f6"
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
                "status": "Configuring",
                "info": {
                    "HDFS": {
                        "NameNode": "hdfs://cluster-template-3-master-001:9000",
                        "Web UI": "http://172.18.168.233:50070"
                    },
                    "JobFlow": {
                        "Oozie": "http://172.18.168.233:11000"
                    },
                    "MapReduce JobHistory Server": {
                        "Web UI": "http://172.18.168.233:19888"
                    },
                    "YARN": {
                        "Web UI": "http://172.18.168.233:8088"
                    }
                },
                "cluster_template_id": null,
                "is_transient": false,
                "description": null,
                "cluster_configs": {
                    "HDFS": {
                        "dfs.replication": 3
                    },
                    "general": {
                        "Enable MySQL": true,
                        "Enable Swift": true
                    }
                },
                "created_at": "2014-09-02 23:34:09",
                "default_image_id": "be23ce84-68cb-490a-b50e-e4f3e340d5d7",
                "user_keypair_id": null,
                "updated_at": "2014-09-02 23:47:28",
                "plugin_name": "vanilla",
                "neutron_management_network": "8b826011-27af-4068-a36a-9488d6d0d1c5",
                "anti_affinity": [],
                "tenant_id": "af8996ec973444048f159f2bf2e3c24e",
                "node_groups": [
                    {
                        "auto_security_group": null,
                        "instances": [
                            {
                                "instance_name": "cluster-template-3-big-worker-001",
                                "created_at": "2014-09-02 23:46:38",
                                "updated_at": "2014-09-02 23:47:02",
                                "instance_id": "3bba57b4-737f-4d84-a441-f1ef456ab0fe",
                                "management_ip": "172.18.168.235",
                                "volumes": [],
                                "internal_ip": "10.50.0.64",
                                "id": "281ea99f-2ef7-42c9-a192-4988d6b5d15b"
                            },
                            {
                                "instance_name": "cluster-template-3-big-worker-002",
                                "created_at": "2014-09-02 23:46:39",
                                "updated_at": "2014-09-02 23:47:03",
                                "instance_id": "edfa4f85-fd6d-41c7-9318-98ab19c53191",
                                "management_ip": "172.18.168.244",
                                "volumes": [],
                                "internal_ip": "10.50.0.65",
                                "id": "54521553-8806-4e64-bd56-4ace7a62566b"
                            }
                        ],
                        "volume_mount_prefix": "/volumes/disk",
                        "created_at": "2014-09-02 23:46:36",
                        "updated_at": "2014-09-02 23:46:39",
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {
                            "HDFS": {
                                "DataNode Heap Size": 1024
                            },
                            "YARN": {
                                "NodeManager Heap Size": 2048
                            }
                        },
                        "node_group_template_id": "734551b4-0542-4bc1-b9bf-85f77d85c6f6",
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "nodemanager"
                        ],
                        "auto_security_group": null,
                        "instances": [
                            {
                                "instance_name": "cluster-template-3-master-001",
                                "created_at": "2014-09-02 23:34:13",
                                "updated_at": "2014-09-02 23:34:56",
                                "instance_id": "c7d17c4f-56fc-46a4-bcd1-76ec3d459d82",
                                "management_ip": "172.18.168.233",
                                "volumes": [],
                                "internal_ip": "10.50.0.59",
                                "id": "47aac1fc-11e2-4f89-b699-69ede345379b"
                            }
                        ],
                        "volume_mount_prefix": "/volumes/disk",
                        "created_at": "2014-09-02 23:34:09",
                        "updated_at": "2014-09-02 23:34:13",
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {},
                        "node_group_template_id": null,
                        "volumes_per_node": 0,
                        "node_processes": [
                            "namenode",
                            "resourcemanager",
                            "oozie",
                            "historyserver"
                        ],
                        "auto_security_group": null,
                        "security_groups": null,
                        "flavor_id": "3"
                    },
                    {
                        "count": 4,
                        "name": "worker",
                        "instances": [
                            {
                                "instance_name": "cluster-template-3-worker-001",
                                "created_at": "2014-09-02 23:34:11",
                                "updated_at": "2014-09-02 23:34:55",
                                "instance_id": "3e2a0cc1-fd25-42c0-885d-efffb11f56e3",
                                "management_ip": "172.18.168.232",
                                "volumes": [],
                                "internal_ip": "10.50.0.57",
                                "id": "e6b41b36-dfa8-49f6-ab19-a3796d510014"
                            },
                            {
                                "instance_name": "cluster-template-3-worker-002",
                                "created_at": "2014-09-02 23:34:12",
                                "updated_at": "2014-09-02 23:34:55",
                                "instance_id": "9e4d5f63-1424-4a8c-b830-b953fb674854",
                                "management_ip": "172.18.168.231",
                                "volumes": [],
                                "internal_ip": "10.50.0.60",
                                "id": "41d8808d-00f1-4887-8791-6ee990307095"
                            },
                            {
                                "instance_name": "cluster-template-3-worker-003",
                                "created_at": "2014-09-02 23:34:12",
                                "updated_at": "2014-09-02 23:34:56",
                                "instance_id": "4e7ecea4-1d2d-46ff-983f-ad3134601662",
                                "management_ip": "172.18.168.234",
                                "volumes": [],
                                "internal_ip": "10.50.0.58",
                                "id": "16d59d71-25fa-42eb-9a7a-f050224dd653"
                            },
                            {
                                "instance_name": "cluster-template-3-worker-004",
                                "created_at": "2014-09-02 23:46:39",
                                "updated_at": "2014-09-02 23:47:03",
                                "instance_id": "6bdd8744-8591-453b-8ad8-27593a97825a",
                                "management_ip": "172.18.168.245",
                                "volumes": [],
                                "internal_ip": "10.50.0.66",
                                "id": "5a930e18-1dbf-4958-8686-32cd4a741048"
                            }
                        ],
                        "volume_mount_prefix": "/volumes/disk",
                        "created_at": "2014-09-02 23:34:09",
                        "updated_at": "2014-09-02 23:46:40",
                        "floating_ip_pool": "77e2c46d-9585-46a2-95f9-8721c302b257",
                        "image_id": null,
                        "volumes_size": 0,
                        "node_configs": {
                            "HDFS": {
                                "DataNode Heap Size": 1024
                            },
                            "YARN": {
                                "NodeManager Heap Size": 2048
                            }
                        },
                        "node_group_template_id": null,
                        "volumes_per_node": 0,
                        "node_processes": [
                            "datanode",
                            "nodemanager"
                        ],
                        "security_groups": null,
                        "flavor_id": "3"
                    }
                ],
                "management_public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwXKFhoOhyyKF3xtFcWv/TYw3lNS27X8AIwbBwUrwhvxYSLSqJO53YL7DRIIBGmzhCb+Y9+oPU50cgwvVvLH0ww7aBpAtsG3dMaEgv2xQzLwEVAy2TJOy+c1cxqaLfyrUlzx1mh4GXsqJlW2qjdDYPhCB1OSL2JIHACqhyZp/5YrgL84Etx6zcJeac+0x4Z3pCbjXzW7oQVRmHdhrcq/aMaX4qhWg3JxnVTflFg4jigGsWM2Cj2VNxdRNiZyyqwLO8YENi8hG6rEcuVWRU/v8N9DaqFj+JumPDQ5S6kBD6mk+5z1oISYUhW/6Syo4CTaHlrMcMoF9Mh9s86wLvW/o1 Generated by Sahara\n",
                "status_description": "",
                "hadoop_version": "2.4.1",
                "id": "b77e8def-a66d-4df8-bc9a-10a9a216fd60",
                "trust_id": null,
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
