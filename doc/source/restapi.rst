Sahara REST API v1.1
*********************

1 General API information
=========================

This section contains base info about the Sahara REST API design.

1.1 Authentication and Authorization
------------------------------------

The Sahara API uses the Keystone Identity Service as the default authentication service.
When Keystone is enabled, users who submit requests to the Sahara service must provide an authentication token
in the X-Auth-Token request header. A user can obtain the token by authenticating to the Keystone endpoint.
For more information about Keystone, see the OpenStack Identity Developer Guide.

Also with each request a user must specify the OpenStack tenant in the url path, for example: '/v1.1/{tenant_id}/clusters'.
Sahara will perform the requested operation in the specified tenant using the provided credentials.
Therefore, clusters may be created and managed only within tenants to which the user has access.

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

    GET /v1.1/{tenant_id}/clusters.json

or

.. sourcecode:: http

    GET /v1.1/{tenant_id}/clusters
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

2 API
=====

-  `Sahara REST API Reference (OpenStack API Complete Reference - DataProcessing)`_

   .. _`Sahara REST API Reference (OpenStack API Complete Reference - DataProcessing)`: http://api.openstack.org/api-ref-data-processing-v1.1.html
