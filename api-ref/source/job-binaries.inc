.. -*- rst -*-

============
Job binaries
============

Job binary objects represent data processing applications and
libraries that are stored in either the internal database or the
Object Storage service.


List job binaries
=================

.. rest_method::  GET /v1.1/{project_id}/job-binaries

Lists the available job binaries.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - limit: limit
   - marker: marker
   - sort_by: sort_by_job_binary



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - markers: markers
   - prev: prev
   - next: next
   - description: job_binary_description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - binaries: binaries
   - id: job_binary_id
   - name: job_binary_name



Response Example
----------------
.. rest_method:: GET /v1.1/{project_id}/job-binaries?sort_by=created_at

.. literalinclude:: samples/job-binaries/list-response.json
   :language: javascript




Create job binary
=================

.. rest_method::  POST /v1.1/{project_id}/job-binaries

Creates a job binary.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id


Request Example
---------------

.. literalinclude:: samples/job-binaries/create-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: job_binary_description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - id: job_binary_id
   - name: job_binary_name





Show job binary details
=======================

.. rest_method::  GET /v1.1/{project_id}/job-binaries/{job_binary_id}

Shows details for a job binary.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_binary_id: url_job_binary_id



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: job_binary_description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - id: job_binary_id
   - name: job_binary_name



Response Example
----------------

.. literalinclude:: samples/job-binaries/show-response.json
   :language: javascript




Delete job binary
=================

.. rest_method::  DELETE /v1.1/{project_id}/job-binaries/{job_binary_id}

Deletes a job binary.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml


   - project_id: url_project_id
   - job_binary_id: url_job_binary_id






Update job binary
=================

.. rest_method::  PUT /v1.1/{project_id}/job-binaries/{job_binary_id}

Updates a job binary.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml


   - project_id: url_project_id
   - job_binary_id: url_job_binary_id


Request Example
---------------

.. literalinclude:: samples/job-binaries/update-request.json
   :language: javascript







Show job binary data
====================

.. rest_method::  GET /v1.1/{project_id}/job-binaries/{job_binary_id}/data

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


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_binary_id: url_job_binary_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - Content-Length: Content-Length



Response Example
----------------

.. literalinclude:: samples/job-binaries/show-data-response
   :language: text



