.. -*- rst -*-

============
Job binaries
============

Job binary objects represent data processing applications and
libraries that are stored in either the internal database or the
Object Storage service.


List job binaries
=================

.. rest_method::  GET /v1.1/{tenant_id}/job-binaries

Lists the available job binaries.


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: is_protected
   - is_public: is_public
   - binaries: binaries
   - id: id
   - name: name



Response Example
----------------

.. literalinclude:: samples/job-binaries/list-response.json
   :language: javascript




Create job binary
=================

.. rest_method::  POST /v1.1/{tenant_id}/job-binaries

Creates a job binary.

Error response codes:202,


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id


Request Example
---------------

.. literalinclude:: samples/job-binaries/create-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: is_protected
   - is_public: is_public
   - id: id
   - name: name





Show job binary details
=======================

.. rest_method::  GET /v1.1/{tenant_id}/job-binaries

Shows details for a job binary.


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: is_protected
   - is_public: is_public
   - id: id
   - name: name



Response Example
----------------

.. literalinclude:: samples/job-binaries/show-response.json
   :language: javascript




Delete job binary
=================

.. rest_method::  DELETE /v1.1/{tenant_id}/job-binaries

Deletes a job binary.

Error response codes:204,


Request
-------

.. rest_parameters:: parameters.yaml


   - tenant_id: url_tenant_id






Update job binary
=================

.. rest_method::  PUT /v1.1/{tenant_id}/job-binaries

Updates a job binary.

Error response codes:202,


Request
-------

.. rest_parameters:: parameters.yaml


   - tenant_id: url_tenant_id


Request Example
---------------

.. literalinclude:: samples/job-binaries/update-request.json
   :language: javascript







Show job binary data
====================

.. rest_method::  GET /v1.1/{tenant_id}/job-binaries/{job_binary_id}/data

Shows data for a job binary.

The response body shows the job binary raw data and the response
headers show the data length.

Example response:

::

   HTTP/1.1 200 OK
   Connection: keep-alive
   Content-Length: 161
   Content-Type: text/html; charset=utf-8
   Date: Sat, 28 Mar 2016 02:42:48 GMT
   A = load '$INPUT' using PigStorage(':') as (fruit: chararray);
   B = foreach A generate com.hadoopbook.pig.Trim(fruit);
   store B into '$OUTPUT' USING PigStorage();


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - job_binary_id: job_binary_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - Content-Length: Content-Length



Response Example
----------------

.. literalinclude:: samples/job-binaries/show-data-response
   :language: text



