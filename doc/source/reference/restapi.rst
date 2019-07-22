Sahara REST API v1.1
********************

1 General API information
=========================

This section contains base info about the sahara REST API design.

1.1 Authentication and Authorization
------------------------------------

The sahara API uses the OpenStack Identity service as the default
authentication service. When the Identity service is enabled, users who
submit requests to the sahara service must provide an authentication token in
the ``X-Auth-Token`` request header. A user can obtain the token by
authenticating to the Identity service endpoint. For more information about
the Identity service, please see the :keystone-doc:`keystone project developer
documentation <>`.

With each request, a user must specify the keystone project
in the url path, for example: '/v1.1/{project_id}/clusters'. Sahara
will perform the requested operation in the specified project using the
provided credentials. Therefore, clusters may be created and managed only
within projects to which the user has access.

1.2 Request / Response Types
----------------------------

The sahara API supports the JSON data serialization format. This means that
for requests that contain a body, the ``Content-Type`` header must be set to
the MIME type value ``application/json``. Also, clients should accept JSON
serialized responses by specifying the ``Accept`` header with the MIME type
value ``application/json`` or adding the ``.json`` extension to the resource
name. The default response format is ``application/json`` if the client does
not specify an ``Accept`` header or append the ``.json`` extension in the URL
path.

Example:

.. sourcecode:: text

    GET /v1.1/{project_id}/clusters.json

or

.. sourcecode:: text

    GET /v1.1/{project_id}/clusters
    Accept: application/json

1.3 Navigation by response
--------------------------
Sahara API supports delivering response data by pages. User can pass
two parameters in API GET requests which return an array of objects.
The parameters are:

``limit`` - maximum number of objects in response data.
This parameter must be a positive integer number.

``marker`` - ID of the last element on the list which won't be in response.

Example:
Get 15 clusters after cluster with id=d62ad147-5c10-418c-a21a-3a6597044f29:

.. sourcecode:: text

    GET /v1.1/{project_id}/clusters?limit=15&marker=d62ad147-5c10-418c-a21a-3a6597044f29

For convenience, response contains markers of previous and following pages
which are named 'prev' and 'next' fields. Also there is ``sort_by`` parameter
for sorting objects. Sahara API supports ascending and descending sorting.

Examples:
Sort clusters by name:

.. sourcecode:: text

    GET /v1.1/{project_id}/clusters?sort_by=name

Sort clusters by date of creation in descending order:

.. sourcecode:: text

    GET /v1.1/{project_id}/clusters?sort_by=-created_at


1.4 Faults
----------
The sahara API returns an error response if a failure occurs while
processing a request. Sahara uses only standard HTTP error codes. 4xx errors
indicate problems in the particular request being sent from the client and
5xx errors indicate server-side problems.

The response body will contain richer information about the cause of the
error. An error response follows the format illustrated by the following
example:

.. sourcecode:: http

    HTTP/1.1 400 BAD REQUEST
    Content-type: application/json
    Content-length: 126

    {
        "error_name": "CLUSTER_NAME_ALREADY_EXISTS",
        "error_message": "Cluster with name 'test-cluster' already exists",
        "error_code": 400
    }


The ``error_code`` attribute is an HTTP response code. The ``error_name``
attribute indicates the generic error type without any concrete ids or
names, etc. The last attribute, ``error_message``, contains a human readable
error description.

2 API
=====

- `Sahara REST API Reference (OpenStack API Complete Reference - DataProcessing) <https://docs.openstack.org/api-ref/data-processing/>`_
