Sahara REST API v1.1 (EDP)
**************************

.. note::

    REST API v1.1 corresponds to Sahara v0.3.X and Sahara Icehouse release

1. General information
======================

REST API v1.1 enhances the :doc:`rest_api_v1.0` and includes all requests from v1.0.
REST API V1.1 is :doc:`../userdoc/edp` REST API. It covers the majority of new functions related to creating job binaries and job objects on running Hadoop clusters.

2. Data Sources
===============

**Description**

A Data Source object provides the location of input or output for MapReduce jobs and may reference different types of storage.
Sahara doesn't perform any validation checks for data source locations.

**Data Source ops**

+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| Verb            | URI                                                               | Description                                         |
+=================+===================================================================+=====================================================+
| GET             | /v1.1/{tenant_id}/data-sources                                    | Lists all Data Sources                              |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.1/{tenant_id}/data-sources/<data_source_id>                   | Shows information about specified Data Source by id |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| POST            | /v1.1/{tenant_id}/data-sources                                    | Create a new Data Source                            |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| DELETE          | /v1.1/{tenant_id}/data-sources/<data_source_id>                   | Removes specified Data Source                       |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+

**Examples**

2.1 List all Data Sources
-------------------------

.. http:get:: /v1.1/{tenant_id}/data-sources

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all created data sources.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/data-sources

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "data_sources": [
                {
                    "description": "This is input",
                    "url": "swift://container.sahara/text",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-09 12:37:19.295701",
                    "updated_at": null,
                    "type": "swift",
                    "id": "151d0c0c-464f-4724-96a6-4732d0ca62e1",
                    "name": "input"
                },
                {
                    "description": "This is output",
                    "url": "swift://container.sahara/result",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-09 12:37:58.155911",
                    "updated_at": null,
                    "type": "swift",
                    "id": "577e8bd8-b105-46f0-ace7-baee61e0adda",
                    "name": "output"
                },
                {
                    "description": "This is hdfs input",
                    "url": "hdfs://test-master-node:8020/user/hadoop/input",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2014-01-23 12:37:24.720387",
                    "updated_at": null,
                    "type": "hdfs",
                    "id": "63e3d1e6-52d0-4d27-ab8a-f8e236ded200",
                    "name": "hdfs_input"
                }
            ]
        }

2.2 Show Data Source
--------------------

.. http:get:: /v1.1/{tenant_id}/data-sources/<data_source_id>

Normal Response Code: 200 (OK)

Errors: none

This operation shows information about a specified Data Source.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/data-sources/151d0c0c-464f-4724-96a6-4732d0ca62e1

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "data_source": {
                "description": "",
                "url": "swift://container.sahara/text",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-09 12:37:19.295701",
                "updated_at": null,
                "type": "swift",
                "id": "151d0c0c-464f-4724-96a6-4732d0ca62e1",
                "name": "input"
            }
        }

2.3 Create Data Source
----------------------

.. http:post:: /v1.1/{tenant_id}/data-sources

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns the created Data Source.

**Example**:

    This example creates a Swift data source.

    **request**

    .. sourcecode:: http

        POST http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/data-sources

    .. sourcecode:: json

        {
            "description": "This is input",
            "url": "swift://container.sahara/text",
            "credentials": {
                "password": "swordfish",
                "user": "admin"
            },
            "type": "swift",
            "name": "text"
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "data_source": {
                "description": "This is input",
                "url": "swift://container.sahara/text",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-15 11:15:25.971886",
                "type": "swift",
                "id": "af7dc864-6331-4c30-80f5-63d74b667eaf",
                "name": "text"
            }
        }

**Example**:

    This example creates an hdfs data source.

    **request**

    .. sourcecode:: http

        POST http://sahara:8386/v1.1/e262c255a7de4a0ab0434bafd75660cd/data-sources

    .. sourcecode:: json

        {
            "description": "This is hdfs input",
            "url": "hdfs://test-master-node:8020/user/hadoop/input",
            "type": "hdfs",
            "name": "hdfs_input"
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "data_source": {
                "description": "This is hdfs input",
                "url": "hdfs://test-master-node:8020/user/hadoop/input",
                "tenant_id": "e262c255a7de4a0ab0434bafd75660cd",
                "created_at": "2014-01-23 12:37:24.720387",
                "type": "hdfs",
                "id": "63e3d1e6-52d0-4d27-ab8a-f8e236ded200",
                "name": "hdfs_input"
            }
        }


2.4 Delete Data Source
----------------------

.. http:delete:: /v1.1/{tenant_id}/data-sources/<data-source-id>

Normal Response Code: 204 (NO CONTENT)

Errors: none

Removes Data Source

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/data-sources/af7dc864-6331-4c30-80f5-63d74b667eaf

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json

3 Job Binary Internals
======================

**Description**

Job Binary Internals are objects for storing job binaries in the Sahara internal database.
A Job Binary Internal contains raw data of executable Jar files, Pig or Hive scripts.

**Job Binary Internal ops**

+-----------------+----------------------------------------------------------------------+-----------------------------------------------------+
| Verb            | URI                                                                  | Description                                         |
+=================+======================================================================+=====================================================+
| GET             | /v1.1/{tenant_id}/job-binary-internals                               | Lists all Job Binary Internals                      |
+-----------------+----------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-binary-internals/<job_binary_internal_id>      | Shows info about specified Job Binary Internal by id|
+-----------------+----------------------------------------------------------------------+-----------------------------------------------------+
| PUT             | /v1.1/{tenant_id}/job-binary-internals/<name>                        | Create a new Job Binary Internal with specified name|
+-----------------+----------------------------------------------------------------------+-----------------------------------------------------+
| DELETE          | /v1.1/{tenant_id}/job-binary-internals/<job_binary_internal_id>      | Removes specified Job Binary Internal               |
+-----------------+----------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-binary-internals/<job_binary_internal_id>/data | Retrieves data of specified Job Binary Internal     |
+-----------------+----------------------------------------------------------------------+-----------------------------------------------------+

**Examples**

3.1 List all Job Binary Internals
---------------------------------

.. http:get:: /v1.1/{tenant_id}/job-binary-internals

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all stored Job Binary Internals.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binary-internals

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "binaries": [
                {
                    "name": "example.pig",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-15 12:36:59.329034",
                    "updated_at": null,
                    "datasize": 161,
                    "id": "d2498cbf-4589-484a-a814-81436c18beb3"
                },
                {
                    "name": "udf.jar",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-15 12:43:52.008620",
                    "updated_at": null,
                    "datasize": 3745,
                    "id": "22f1d87a-23c8-483e-a0dd-cb4a16dde5f9"
                }
            ]
        }

3.2 Show Job Binary Internal
----------------------------

.. http:get:: /v1.1/{tenant_id}/job-binary-internals/<job_binary_internal_id>

Normal Response Code: 200 (OK)

Errors: none

This operation shows information about a specified Job Binary Internal.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binary-internals/d2498cbf-4589-484a-a814-81436c18beb3

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_binary_internal": {
                "name": "example.pig",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-15 12:36:59.329034",
                "updated_at": null,
                "datasize": 161,
                "id": "d2498cbf-4589-484a-a814-81436c18beb3"
            }
        }

3.3 Create Job Binary Internal
------------------------------

.. http:put:: /v1.1/{tenant_id}/job-binary-internals/<name>

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation shows information about the uploaded Job Binary Internal.

The request body should contain raw data (file) or script text.

**Example**:
    **request**

    .. sourcecode:: http

        PUT http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binary-internals/script.pig

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_binary_internal": {
                "name": "script.pig",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-15 13:17:35.994466",
                "updated_at": null,
                "datasize": 160,
                "id": "4833dc4b-8682-4d5b-8a9f-2036b47a0996"
            }
        }

3.4 Delete Job Binary Internal
------------------------------

.. http:delete:: /v1.1/{tenant_id}/job-binary-internals/<job_binary_internal_id>

Normal Response Code: 204 (NO CONTENT)

Errors: none

Removes Job Binary Internal object from Sahara's db

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binary-internals/4833dc4b-8682-4d5b-8a9f-2036b47a0996

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json

3.5 Get Job Binary Internal data
--------------------------------

.. http:get:: /v1.1/{tenant_id}/job-binary-internals/<job_binary_internal_id>/data

Normal Response Code: 200 (OK)

Errors: none

Retrieves data of specified Job Binary Internal object.

This operation returns raw data.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binary-internals/4248975-3c82-4206-a58d-6e7fb3a563fd/data

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Length: 161
        Content-Type: text/html; charset=utf-8

4. Job Binaries
===============

**Description**

Job Binaries objects are designed to create links to certain binaries stored either in the Sahara internal database or in Swift.

**Job Binaries ops**

+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| Verb            | URI                                                               | Description                                         |
+=================+===================================================================+=====================================================+
| GET             | /v1.1/{tenant_id}/job-binaries                                    | Lists all Job Binaries                              |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-binaries/<job_binary_id>                    | Shows info about specified Job Binary by id         |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| POST            | /v1.1/{tenant_id}/job-binaries                                    | Create a new Job Binary object                      |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| DELETE          | /v1.1/{tenant_id}/job-binaries/<job_binary_id>                    | Removes specified Job Binary                        |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-binaries/<job_binary_id>/data               | Retrieves data of specified Job Binary              |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------+

**Examples**

4.1 List all Job Binaries
-------------------------

.. http:get:: /v1.1/{tenant_id}/job-binaries

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all created Job Binaries.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binaries

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "binaries": [
                {
                    "description": "",
                    "url": "internal-db://d2498cbf-4589-484a-a814-81436c18beb3",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-15 12:36:59.375060",
                    "updated_at": null,
                    "id": "84248975-3c82-4206-a58d-6e7fb3a563fd",
                    "name": "example.pig"
                },
                {
                    "description": "",
                    "url": "internal-db://22f1d87a-23c8-483e-a0dd-cb4a16dde5f9",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-15 12:43:52.265899",
                    "updated_at": null,
                    "id": "508fc62d-1d58-4412-b603-bdab307bb926",
                    "name": "udf.jar"
                },
                {
                    "description": "",
                    "url": "swift://container/jar-example.jar",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-15 14:25:04.970513",
                    "updated_at": null,
                    "id": "a716a9cd-9add-4b12-b1b6-cdb71aaef350",
                    "name": "jar-example.jar"
                }
            ]
        }

4.2 Show Job Binary
-------------------

.. http:get:: /v1.1/{tenant_id}/job-binaries/<job_binary_id>

Normal Response Code: 200 (OK)

Errors: none

This operation shows information about a specified Job Binary.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binaries/a716a9cd-9add-4b12-b1b6-cdb71aaef350

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_binary": {
                "description": "",
                "url": "swift://container/jar-example.jar",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-15 14:25:04.970513",
                "updated_at": null,
                "id": "a716a9cd-9add-4b12-b1b6-cdb71aaef350",
                "name": "jar-example.jar"
            }
        }

4.3 Create Job Binary
---------------------

.. http:post:: /v1.1/{tenant_id}/job-binaries

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation shows information about the created Job Binary.

**Example**:
    **request**

    .. sourcecode:: http

        POST http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binaries

    .. sourcecode:: json

        {
            "url": "swift://container/jar-example.jar",
            "name": "jar-example.jar",
            "description": "This is job binary",
            "extra": {
              "password": "swordfish",
              "user": "admin"
            }
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_binary": {
                "description": "This is job binary",
                "url": "swift://container/jar-example.jar",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-15 14:49:20.106452",
                "id": "07f86352-ee8a-4b08-b737-d705ded5ff9c",
                "name": "jar-example.jar"
            }
        }

4.4 Delete Job Binary
---------------------

.. http:delete:: /v1.1/{tenant_id}/job-binaries/<job_binary_id>

Normal Response Code: 204 (NO CONTENT)

Errors: none

Removes Job Binary object

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binaries/07f86352-ee8a-4b08-b737-d705ded5ff9c

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json

4.5 Get Job Binary data
-----------------------

.. http:get:: /v1.1/{tenant_id}/job-binaries/<job_binary_id>/data

Normal Response Code: 200 (OK)

Errors: none

Retrieves data of specified Job Binary object.

This operation returns raw data.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/job-binaries/84248975-3c82-4206-a58d-6e7fb3a563fd/data

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Length: 161
        Content-Type: text/html; charset=utf-8

5. Jobs
=======

**Description**

Job objects represent Hadoop jobs.
A Job object contains lists of all binaries needed for job execution.
User should provide data sources and Job parameters to start job execution.
A Job may be run on an existing cluster or a new transient cluster may be created for the Job run.

**Job ops**

+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| Verb            | URI                                                               | Description                                            |
+=================+===================================================================+========================================================+
| GET             | /v1.1/{tenant_id}/jobs                                            | Lists all created Jobs                                 |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/jobs/<job_id>                                   | Shows info about specified Job by id                   |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| POST            | /v1.1/{tenant_id}/jobs                                            | Create a new Job object                                |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| DELETE          | /v1.1/{tenant_id}/jobs/<job_id>                                   | Removes specified Job                                  |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/jobs/config-hints/<job_type>                    | Shows default configuration for Job type (deprecated)  |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+
| POST            | /v1.1/{tenant_id}/jobs/<job_id>/execute                           | Starts Job executing                                   |
+-----------------+-------------------------------------------------------------------+--------------------------------------------------------+

**Examples**

5.1 List all Jobs
-----------------

.. http:get:: /v1.1/{tenant_id}/jobs

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all created Jobs.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/jobs

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "jobs": [
                {
                    "description": "",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-16 11:26:54.109123",
                    "mains": [
                        {
                            "description": "",
                            "url": "internal-db://d2498cbf-4589-484a-a814-81436c18beb3",
                            "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                            "created_at": "2013-10-15 12:36:59.375060",
                            "updated_at": null,
                            "id": "84248975-3c82-4206-a58d-6e7fb3a563fd",
                            "name": "example.pig"
                        }
                    ],
                    "updated_at": null,
                    "libs": [
                        {
                            "description": "",
                            "url": "internal-db://22f1d87a-23c8-483e-a0dd-cb4a16dde5f9",
                            "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                            "created_at": "2013-10-15 12:43:52.265899",
                            "updated_at": null,
                            "id": "508fc62d-1d58-4412-b603-bdab307bb926",
                            "name": "udf.jar"
                        }
                    ],
                    "type": "Pig",
                    "id": "65afed9c-dad7-4658-9554-b7b4e1ca908f",
                    "name": "pig-job"
                },
                {
                    "description": "",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "created_at": "2013-10-16 11:29:55.008351",
                    "mains": [],
                    "updated_at": null,
                    "libs": [
                        {
                            "description": "This is job binary",
                            "url": "swift://container/jar-example.jar",
                            "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                            "created_at": "2013-10-15 16:03:37.979630",
                            "updated_at": null,
                            "id": "8955b12f-ed32-4152-be39-5b7398c3d04c",
                            "name": "hadoopexamples.jar"
                        }
                    ],
                    "type": "Jar",
                    "id": "7600373c-d262-45c6-845f-77f339f3e503",
                    "name": "jar-job"
                }
            ]
        }

5.2 Show Job
------------

.. http:get:: /v1.1/{tenant_id}/jobs/<job_id>

Normal Response Code: 200 (OK)

Errors: none

This operation returns the information about the specified Job.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/jobs/7600373c-d262-45c6-845f-77f339f3e503

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job": {
                "description": "",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-16 11:29:55.008351",
                "mains": [],
                "updated_at": null,
                "libs": [
                    {
                        "description": "This is job binary",
                        "url": "swift://container/jar-example.jar",
                        "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                        "created_at": "2013-10-15 16:03:37.979630",
                        "updated_at": null,
                        "id": "8955b12f-ed32-4152-be39-5b7398c3d04c",
                        "name": "hadoopexamples.jar"
                    }
                ],
                "type": "Jar",
                "id": "7600373c-d262-45c6-845f-77f339f3e503",
                "name": "jar-job"
            }
        }

5.3 Create Job
--------------

.. http:post:: /v1.1/{tenant_id}/jobs

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation shows information about the created Job object.

**Example**:
    **request**

    .. sourcecode:: http

        POST http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/jobs

    .. sourcecode:: json

        {
            "description": "This is pig job example",
            "mains": ["84248975-3c82-4206-a58d-6e7fb3a563fd"],
            "libs": ["508fc62d-1d58-4412-b603-bdab307bb926"],
            "type": "Pig",
            "name": "pig-job-example"
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job": {
                "description": "This is pig job example",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-17 09:52:20.957275",
                "mains": [
                    {
                        "description": "",
                        "url": "internal-db://d2498cbf-4589-484a-a814-81436c18beb3",
                        "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                        "created_at": "2013-10-15 12:36:59.375060",
                        "updated_at": null,
                        "id": "84248975-3c82-4206-a58d-6e7fb3a563fd",
                        "name": "example.pig"
                    }
                ],
                "libs": [
                    {
                        "description": "",
                        "url": "internal-db://22f1d87a-23c8-483e-a0dd-cb4a16dde5f9",
                        "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                        "created_at": "2013-10-15 12:43:52.265899",
                        "updated_at": null,
                        "id": "508fc62d-1d58-4412-b603-bdab307bb926",
                        "name": "udf.jar"
                    }
                ],
                "type": "Pig",
                "id": "3cb27eaa-2f88-4c75-ab81-a36e2ab58d4e",
                "name": "pig-job-example"
            }
        }

5.4 Delete Job
--------------

.. http:delete:: /v1.1/{tenant_id}/jobs/<job_id>

Normal Response Code: 204 (NO CONTENT)

Errors: none

Removes the Job object

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/jobs/07f86352-ee8a-4b08-b737-d705ded5ff9c

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json

5.5 Show Job Configuration Hints
--------------------------------

.. http:get:: /v1.1/{tenant_id}/jobs/config-hints/<job-type>

Normal Response Code: 200 (OK)

Errors: none

This operation returns hints for configuration parameters which can be applied during job execution.

(deprecated) For config-hints, the *job-types* endpoint should be used instead.

This operation does not require a request body.

**Note**
This REST call is used just for hints and doesn't force the user to apply any of them.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.1/11587919cc534bcbb1027a161c82cf58/jobs/config-hints/MapReduce

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_config": {
                "configs": [
                     {
                        "name": "mapred.reducer.new-api",
                        "value": "true",
                        "description": ""
                    },
                    {
                        "name": "mapred.mapper.new-api",
                        "value": "true",
                        "description": ""
                    },
                    {
                        "name": "mapred.input.dir",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapred.output.dir",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapred.mapoutput.key.class",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapred.mapoutput.value.class",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapred.output.key.class",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapred.output.value.class",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapreduce.map.class",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapreduce.reduce.class",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapred.mapper.class",
                        "value": "",
                        "description": ""
                    },
                    {
                        "name": "mapred.reducer.class",
                        "value": "",
                        "description": ""
                    }
                ],
                "args": []
            }
        }

5.6 Execute Job
---------------

.. http:post:: /v1.1/{tenant_id}/jobs/<job_id>/execute

Normal Response Code: 202 (ACCEPTED)

Errors: none

This operation returns the created Job Execution object. Note that different job types support different combinations of ``configs``, ``args``, and ``params``.  The :doc:`../userdoc/edp` document discusses these differences.

**Example execution of a Pig job**:
    **request**

    .. sourcecode:: http

        POST http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/jobs/65afed9c-dad7-4658-9554-b7b4e1ca908f/execute

    .. sourcecode:: json

        {
            "cluster_id": "776e441b-5816-4d47-9e07-7ded58f9a5f6",
            "input_id": "af7dc864-6331-4c30-80f5-63d74b667eaf",
            "output_id": "b63780f3-13d7-4286-b731-88270fb204de",
            "job_configs": {
                "configs": {
                    "mapred.map.tasks": "1",
                    "mapred.reduce.tasks": "1"
                },
                "args": ["arg1", "arg2"],
                "params": {
                    "param2": "value2",
                    "param1": "value1"
                }
            }
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_execution": {
                "output_id": "b63780f3-13d7-4286-b731-88270fb204de",
                "info": {
                    "status": "PENDING"
                },
                "job_id": "65afed9c-dad7-4658-9554-b7b4e1ca908f",
                "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                "created_at": "2013-10-17 13:17:03.631362",
                "input_id": "af7dc864-6331-4c30-80f5-63d74b667eaf",
                "cluster_id": "776e441b-5816-4d47-9e07-7ded58f9a5f6",
                "job_configs": {
                    "configs": {
                        "mapred.map.tasks": "1",
                        "mapred.reduce.tasks": "1"
                    },
                    "args": ["arg1", "arg2"],
                    "params": {
                        "param2": "value2",
                        "param1": "value1"
                    }
                },
                "id": "fb2ba667-1162-4f6d-ba77-662c04dfac35"
            }
        }

**Example execution of a Java job**:

    The main class is specified with ``edp.java.main_class``.  The input/output paths are passed in ``args`` because Java jobs do not use data sources. Finally, the swift configs must be specified because the input/output paths are swift paths.

    **request**

    .. sourcecode:: http

        POST http://sahara:8386/v1.1/11587919cc534bcbb1027a161c82cf58/jobs/65afed9c-dad7-4658-9554-b7b4e1ca908f/execute

    .. sourcecode:: json

        {
            "cluster_id": "776e441b-5816-4d47-9e07-7ded58f9a5f6",
            "job_configs": {
                "configs": {
                    "fs.swift.service.sahara.username": "myname",
                    "fs.swift.service.sahara.password": "mypassword",
                    "edp.java.main_class": "org.apache.hadoop.examples.WordCount"
                },
                "args": ["swift://integration.sahara/demo/make_job.sh", "swift://integration.sahara/friday"]
            }
        }

    **response**

    .. sourcecode:: http

        HTTP/1.1 202 ACCEPTED
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_execution": {
                "output_id": null,
                "info": {
                    "status": "PENDING"
                },
                "job_id": "8236b1b4-e1b8-46ef-9174-355cd4234b62",
                "tenant_id": "a4e4599e87e04bf1996862ae295f6f53",
                "created_at": "2014-02-05 23:31:57.752897",
                "input_id": null,
                "cluster_id": "466a2b6d-df00-4310-b985-c106f5231ec0",
                "job_configs": {
                    "configs": {
                        "edp.java.main_class": "org.apache.hadoop.examples.WordCount",
                        "fs.swift.service.sahara.password": "myname",
                        "fs.swift.service.sahara.username": "mypassword"
                    },
                    "args": [
                        "swift://integration.sahara/demo/make_job.sh",
                        "swift://integration.sahara/friday"
                    ]
                },
                "id": "724709bf-2268-46ed-8daf-47898b4630b4"
            }
        }


6. Job Executions
=================

**Description**

A Job Execution object represents a Hadoop Job executing on specified cluster.
A Job Execution polls the status of a running Job and reports it to the user.
Also a user has the ability to cancel a running job.

**Job Executions ops**

+-----------------+-------------------------------------------------------------------+-----------------------------------------------------------+
| Verb            | URI                                                               | Description                                               |
+=================+===================================================================+===========================================================+
| GET             | /v1.1/{tenant_id}/job-executions                                  | Lists all Job Executions                                  |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-executions/<job_execution_id>               | Shows info about specified Job Execution by id            |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-executions/<job_execution_id>/refresh-status| Refreshes status and shows info about specified Job by id |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-executions/<job_execution_id>/cancel        | Cancels specified Job by id                               |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------------+
| DELETE          | /v1.1/{tenant_id}/job-executions/<job_execution_id>               | Removes specified Job                                     |
+-----------------+-------------------------------------------------------------------+-----------------------------------------------------------+

**Examples**

6.1 List all Job Executions
---------------------------

.. http:get:: /v1.1/{tenant_id}/job-executions

Normal Response Code: 200 (OK)

Errors: none

This operation returns the list of all Job Executions.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.1/11587919cc534bcbb1027a161c82cf58/job-executions

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_executions": [
                {
                    "output_id": "b63780f3-13d7-4286-b731-88270fb204de",
                    "info": {
                        "status": "RUNNING",
                        "externalId": null,
                        "run": 0,
                        "startTime": "Thu, 17 Oct 2013 13:53:14 GMT",
                        "appName": "job-wf",
                        "lastModTime": "Thu, 17 Oct 2013 13:53:17 GMT",
                        "actions": [
                            {
                                "status": "OK",
                                "retries": 0,
                                "transition": "job-node",
                                "stats": null,
                                "startTime": "Thu, 17 Oct 2013 13:53:14 GMT",
                                "cred": "null",
                                "errorMessage": null,
                                "externalId": "-",
                                "errorCode": null,
                                "consoleUrl": "-",
                                "toString": "Action name[:start:] status[OK]",
                                "externalStatus": "OK",
                                "conf": "",
                                "type": ":START:",
                                "trackerUri": "-",
                                "externalChildIDs": null,
                                "endTime": "Thu, 17 Oct 2013 13:53:15 GMT",
                                "data": null,
                                "id": "0000000-131017135256789-oozie-hado-W@:start:",
                                "name": ":start:"
                            },
                            {
                                "status": "RUNNING",
                                "retries": 0,
                                "transition": null,
                                "stats": null,
                                "startTime": "Thu, 17 Oct 2013 13:53:15 GMT",
                                "cred": "null",
                                "errorMessage": null,
                                "externalId": "job_201310171352_0001",
                                "errorCode": null,
                                "consoleUrl": "http://edp-master-001:50030/jobdetails.jsp?jobid=job_201310171352_0001",
                                "toString": "Action name[job-node] status[RUNNING]",
                                "externalStatus": "RUNNING",
                                "conf": "<pig xmlns=\"uri:oozie:workflow:0.2\">\r\n  <job-tracker>edp-master-001:8021</job-tracker>\r\n  <name-node>hdfs://edp-master-001:8020</name-node>\r\n  <configuration>\r\n    <property>\r\n      <name>fs.swift.service.sahara.password</name>\r\n      <value>swordfish</value>\r\n    </property>\r\n    <property>\r\n      <name>fs.swift.service.sahara.username</name>\r\n      <value>admin</value>\r\n    </property>\r\n  </configuration>\r\n  <script>example.pig</script>\r\n  <param>INPUT=swift://container.sahara/text</param>\r\n  <param>OUTPUT=swift://container.sahara/output</param>\r\n</pig>",
                                "type": "pig",
                                "trackerUri": "edp-master-001:8021",
                                "externalChildIDs": null,
                                "endTime": null,
                                "data": null,
                                "id": "0000000-131017135256789-oozie-hado-W@job-node",
                                "name": "job-node"
                            }
                        ],
                        "acl": null,
                        "consoleUrl": "http://edp-master-001.novalocal:11000/oozie?job=0000000-131017135256789-oozie-hado-W",
                        "appPath": "hdfs://edp-master-001:8020/user/hadoop/pig-job/9ceb6469-4d06-474d-995d-76fbc3b8c617/workflow.xml",
                        "toString": "Workflow id[0000000-131017135256789-oozie-hado-W] status[RUNNING]",
                        "user": "hadoop",
                        "conf": "<configuration>\r\n  <property>\r\n    <name>user.name</name>\r\n    <value>hadoop</value>\r\n  </property>\r\n  <property>\r\n    <name>oozie.use.system.libpath</name>\r\n    <value>true</value>\r\n  </property>\r\n  <property>\r\n    <name>nameNode</name>\r\n    <value>hdfs://edp-master-001:8020</value>\r\n  </property>\r\n  <property>\r\n    <name>jobTracker</name>\r\n    <value>edp-master-001:8021</value>\r\n  </property>\r\n  <property>\r\n    <name>oozie.wf.application.path</name>\r\n    <value>hdfs://edp-master-001:8020/user/hadoop/pig-job/9ceb6469-4d06-474d-995d-76fbc3b8c617/workflow.xml</value>\r\n  </property>\r\n</configuration>",
                        "parentId": null,
                        "createdTime": "Thu, 17 Oct 2013 13:53:14 GMT",
                        "group": null,
                        "endTime": null,
                        "id": "0000000-131017135256789-oozie-hado-W"
                    },
                    "job_id": "65afed9c-dad7-4658-9554-b7b4e1ca908f",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "start_time": "2013-10-17T17:53:14",
                    "updated_at": "2013-10-17 13:53:32.227919",
                    "return_code": null,
                    "oozie_job_id": "0000000-131017135256789-oozie-hado-W",
                    "input_id": "af7dc864-6331-4c30-80f5-63d74b667eaf",
                    "end_time": null,
                    "cluster_id": "eb85e8a0-510c-489f-b78e-ad1d29e957c8",
                    "id": "e63bdc21-0126-4fd2-90c6-5163d16f31df",
                    "progress": null,
                    "job_configs": {},
                    "created_at": "2013-10-17 13:51:11.671977"
                },
                {
                    "output_id": "b63780f3-13d7-4286-b731-88270fb204de",
                    "info": {
                        "status": "PENDING"
                    },
                    "job_id": "65afed9c-dad7-4658-9554-b7b4e1ca908f",
                    "tenant_id": "11587919cc534bcbb1027a161c82cf58",
                    "start_time": null,
                    "updated_at": null,
                    "return_code": null,
                    "oozie_job_id": null,
                    "input_id": "af7dc864-6331-4c30-80f5-63d74b667eaf",
                    "end_time": null,
                    "cluster_id": "eb85e8a0-510c-489f-b78e-ad1d29e957c8",
                    "id": "e63bdc21-0126-4fd2-90c6-5163d16f31df",
                    "progress": null,
                    "job_configs": {},
                    "created_at": "2013-10-17 14:37:04.107096"
                }
            ]
        }

6.2 Show Job Execution
----------------------

.. http:get:: /v1.1/{tenant_id}/job-executions/<job_execution_id>

Normal Response Code: 200 (OK)

Errors: none

This operation shows the information about a specified Job Execution.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.1/11587919cc534bcbb1027a161c82cf58/job-executions/e63bdc21-0126-4fd2-90c6-5163d16f31df

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    Response body contains :ref:`job-execution-label`


6.3 Refresh Job Execution status
--------------------------------

.. http:get:: /v1.1/{tenant_id}/job-executions/<job-execution-id>/refresh-status

Normal Response Code: 200 (OK)

Errors: none

This operation refreshes the status of the specified Job Execution and shows its information.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.1/11587919cc534bcbb1027a161c82cf58/job-executions/4a911624-1e25-4650-bd1d-382d19695708/refresh-status

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    Response body contains :ref:`job-execution-label`


6.4 Cancel Job Execution
------------------------

.. http:get:: /v1.1/{tenant_id}/job-executions/<job-execution-id>/cancel

Normal Response Code: 200 (OK)

Errors: none

This operation cancels specified Job Execution.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.1/11587919cc534bcbb1027a161c82cf58/job-executions/4a911624-1e25-4650-bd1d-382d19695708/refresh-status

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    Response body contains :ref:`job-execution-label` with Job Execution in KILLED state


6.5 Delete Job Execution
------------------------

.. http:delete:: /v1.1/{tenant_id}/job-executions/<job-execution-id>

Normal Response Code: 204 (NO CONTENT)

Errors: none

Remove an existing Job Execution.

This operation returns nothing.

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        DELETE http://sahara/v1.1/job-executions/<job-execution-id>/d7g51a-8123-424e-sdsr3-eb222ec989b1

    **response**

    .. sourcecode:: http

        HTTP/1.1 204 NO CONTENT
        Content-Type: application/json

.. _job-execution-label:

Job Execution object
====================

The following json response represents a Job Execution object returned from Sahara

.. sourcecode:: json

    {
        "output_id": "b63780f3-13d7-4286-b731-88270fb204de",
        "info": {
            "status": "RUNNING",
            "externalId": null,
            "run": 0,
            "startTime": "Thu, 17 Oct 2013 13:53:14 GMT",
            "appName": "job-wf",
            "lastModTime": "Thu, 17 Oct 2013 13:53:17 GMT",
            "actions": [
                {
                    "status": "OK",
                    "retries": 0,
                    "transition": "job-node",
                    "stats": null,
                    "startTime": "Thu, 17 Oct 2013 13:53:14 GMT",
                    "cred": "null",
                    "errorMessage": null,
                    "externalId": "-",
                    "errorCode": null,
                    "consoleUrl": "-",
                    "toString": "Action name[:start:] status[OK]",
                    "externalStatus": "OK",
                    "conf": "",
                    "type": ":START:",
                    "trackerUri": "-",
                    "externalChildIDs": null,
                    "endTime": "Thu, 17 Oct 2013 13:53:15 GMT",
                    "data": null,
                    "id": "0000000-131017135256789-oozie-hado-W@:start:",
                    "name": ":start:"
                },
                {
                    "status": "RUNNING",
                    "retries": 0,
                    "transition": null,
                    "stats": null,
                    "startTime": "Thu, 17 Oct 2013 13:53:15 GMT",
                    "cred": "null",
                    "errorMessage": null,
                    "externalId": "job_201310171352_0001",
                    "errorCode": null,
                    "consoleUrl": "http://edp-master-001:50030/jobdetails.jsp?jobid=job_201310171352_0001",
                    "toString": "Action name[job-node] status[RUNNING]",
                    "externalStatus": "RUNNING",
                    "conf": "<pig xmlns=\"uri:oozie:workflow:0.2\">\r\n  <job-tracker>edp-master-001:8021</job-tracker>\r\n  <name-node>hdfs://edp-master-001:8020</name-node>\r\n  <configuration>\r\n    <property>\r\n      <name>fs.swift.service.sahara.password</name>\r\n      <value>swordfish</value>\r\n    </property>\r\n    <property>\r\n      <name>fs.swift.service.sahara.username</name>\r\n      <value>admin</value>\r\n    </property>\r\n  </configuration>\r\n  <script>example.pig</script>\r\n  <param>INPUT=swift://container.sahara/text</param>\r\n  <param>OUTPUT=swift://container.sahara/output</param>\r\n</pig>",
                    "type": "pig",
                    "trackerUri": "edp-master-001:8021",
                    "externalChildIDs": null,
                    "endTime": null,
                    "data": null,
                    "id": "0000000-131017135256789-oozie-hado-W@job-node",
                    "name": "job-node"
                }
            ],
            "acl": null,
            "consoleUrl": "http://edp-master-001.novalocal:11000/oozie?job=0000000-131017135256789-oozie-hado-W",
            "appPath": "hdfs://edp-master-001:8020/user/hadoop/pig-job/9ceb6469-4d06-474d-995d-76fbc3b8c617/workflow.xml",
            "toString": "Workflow id[0000000-131017135256789-oozie-hado-W] status[RUNNING]",
            "user": "hadoop",
            "conf": "<configuration>\r\n  <property>\r\n    <name>user.name</name>\r\n    <value>hadoop</value>\r\n  </property>\r\n  <property>\r\n    <name>oozie.use.system.libpath</name>\r\n    <value>true</value>\r\n  </property>\r\n  <property>\r\n    <name>nameNode</name>\r\n    <value>hdfs://edp-master-001:8020</value>\r\n  </property>\r\n  <property>\r\n    <name>jobTracker</name>\r\n    <value>edp-master-001:8021</value>\r\n  </property>\r\n  <property>\r\n    <name>oozie.wf.application.path</name>\r\n    <value>hdfs://edp-master-001:8020/user/hadoop/pig-job/9ceb6469-4d06-474d-995d-76fbc3b8c617/workflow.xml</value>\r\n  </property>\r\n</configuration>",
            "parentId": null,
            "createdTime": "Thu, 17 Oct 2013 13:53:14 GMT",
            "group": null,
            "endTime": null,
            "id": "0000000-131017135256789-oozie-hado-W"
        },
        "job_id": "65afed9c-dad7-4658-9554-b7b4e1ca908f",
        "tenant_id": "11587919cc534bcbb1027a161c82cf58",
        "start_time": "2013-10-17T17:53:14",
        "updated_at": "2013-10-17 13:53:32.227919",
        "return_code": null,
        "oozie_job_id": "0000000-131017135256789-oozie-hado-W",
        "input_id": "af7dc864-6331-4c30-80f5-63d74b667eaf",
        "end_time": null,
        "cluster_id": "eb85e8a0-510c-489f-b78e-ad1d29e957c8",
        "id": "e63bdc21-0126-4fd2-90c6-5163d16f31df",
        "progress": null,
        "job_configs": {},
        "created_at": "2013-10-17 13:51:11.671977"
    }


7 Job Types
===========

**Description**

Each plugin that supports EDP will support specific job types.
Different versions of a plugin may actually support different job types.
Configuration options will vary by plugin, version, and job type.

This endpoint provides information on which job types are supported by
which plugins and optionally how they may be configured.

**Job Binary Internal ops**

+-----------------+------------------------------------------------------+----------------------------------------------------------+
| Verb            | URI                                                  | Description                                              |
+=================+======================================================+==========================================================+
| GET             | /v1.1/{tenant_id}/job-types                          | Lists job types supported by all versions of all plugins |
+-----------------+------------------------------------------------------+----------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-types?plugin=<plugin_name>     | Filter results by plugin name                            |
+-----------------+------------------------------------------------------+----------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-types?version=<plugin_version> | Filter results by plugin version                         |
+-----------------+------------------------------------------------------+----------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-types?type=<job_type>          | Filter results by job type                               |
+-----------------+------------------------------------------------------+----------------------------------------------------------+
| GET             | /v1.1/{tenant_id}/job-types?hints=true               | Include configuration hints in results                   |
+-----------------+------------------------------------------------------+----------------------------------------------------------+

Note that multiple search filters may be combined in the query string with *&* (for example ?type=Java&type=Pig&plugin=vanilla).

**Examples**

7.1 List all Job Types
----------------------

.. http:get:: /v1.1/{tenant_id}/job-types

Normal Response Code: 200 (OK)

Errors: none

For all job types show which versions of which plugins support them

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/775181/job-types

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_types": [
                {
                    "name": "Hive",
                    "plugins": [
                        {
                            "description": "The Apache Vanilla plugin.",
                            "name": "vanilla",
                            "title": "Vanilla Apache Hadoop",
                            "versions": {
                                "1.2.1": {}
                            }
                        },
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "1.3.2": {},
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "Java",
                    "plugins": [
                        {
                            "description": "The Apache Vanilla plugin.",
                            "name": "vanilla",
                            "title": "Vanilla Apache Hadoop",
                            "versions": {
                                "1.2.1": {}
                            }
                        },
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "1.3.2": {},
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "MapReduce",
                    "plugins": [
                        {
                            "description": "The Apache Vanilla plugin.",
                            "name": "vanilla",
                            "title": "Vanilla Apache Hadoop",
                            "versions": {
                                "1.2.1": {}
                            }
                        },
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "1.3.2": {},
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "MapReduce.Streaming",
                    "plugins": [
                        {
                            "description": "The Apache Vanilla plugin.",
                            "name": "vanilla",
                            "title": "Vanilla Apache Hadoop",
                            "versions": {
                                "1.2.1": {}
                            }
                        },
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "1.3.2": {},
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "Pig",
                    "plugins": [
                        {
                            "description": "The Apache Vanilla plugin.",
                            "name": "vanilla",
                            "title": "Vanilla Apache Hadoop",
                            "versions": {
                                "1.2.1": {}
                            }
                        },
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "1.3.2": {},
                                "2.0.6": {}
                            }
                        }
                    ]
                }
            ]
        }

7.2 List a subset of Job Types
------------------------------

.. http:get:: /v1.1/{tenant_id}/job-types?type=<job_type>&type=<job_type>

Normal Response Code: 200 (OK)

Errors: none

For the specified job types show which versions of which plugins support them

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/775181/job-types?type=Hive&type=Java

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_types": [
                {
                    "name": "Hive",
                    "plugins": [
                        {
                            "description": "The Apache Vanilla plugin.",
                            "name": "vanilla",
                            "title": "Vanilla Apache Hadoop",
                            "versions": {
                                "1.2.1": {}
                            }
                        },
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "1.3.2": {},
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "Java",
                    "plugins": [
                        {
                            "description": "The Apache Vanilla plugin.",
                            "name": "vanilla",
                            "title": "Vanilla Apache Hadoop",
                            "versions": {
                                "1.2.1": {}
                            }
                        },
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "1.3.2": {},
                                "2.0.6": {}
                            }
                        }
                    ]
                }
            ]
        }

7.3 List all Job Types supported by a plugin version
----------------------------------------------------

.. http:get:: /v1.1/{tenant_id}/job-types?plugin=<plugin_name>&version=<plugin_version>

Normal Response Code: 200 (OK)

Errors: none

Show all of the job types that are supported by a specified version
of a specified plugin

This operation does not require a request body.

**Example**:
    **request**

    .. sourcecode:: http

        GET http://sahara:8386/v1.1/775181/job-types?plugin=hdp&version=2.0.6

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_types": [
                {
                    "name": "Hive",
                    "plugins": [
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "Java",
                    "plugins": [
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "MapReduce",
                    "plugins": [
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "MapReduce.Streaming",
                    "plugins": [
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "2.0.6": {}
                            }
                        }
                    ]
                },
                {
                    "name": "Pig",
                    "plugins": [
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "2.0.6": {}
                            }
                        }
                    ]
                }
            ]
        }

7.4 Show configuration hints for a specific Job Type supported by a specific plugin version
-------------------------------------------------------------------------------------------

.. http:get:: /v1.1/{tenant_id}/job-types?hints=true&plugin=<plugin_name>&version=<plugin_version>&type=<job_type>

Normal Response Code: 200 (OK)

Errors: none

Show the configuration hints for a single job type supported by a particular plugin version

This operation does not require a request body.

**Example**
    **request**

    .. sourcecode:: http

        GET http://sahara/v1.1/775181/job-types?hints=true&plugin=hdp&version=1.3.2&type=Hive

    **response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

    .. sourcecode:: json

        {
            "job_types": [
                {
                    "name": "Hive",
                    "plugins": [
                        {
                            "description": "The Hortonworks Sahara plugin.",
                            "name": "hdp",
                            "title": "Hortonworks Data Platform",
                            "versions": {
                                "1.3.2": {
                                    "job_config": {
                                        "args": {},
                                        "configs": [
                                            {
                                                "description": "Reduce tasks.",
                                                "name": "mapred.reduce.tasks",
                                                "value": "-1"
                                            }
                                        ],
                                        "params": {}
                                    }
                                }
                            }
                        }
                    ]
                }
            ]
        }


This is an abbreviated example that shows imaginary config hints.
