.. -*- rst -*-

====================
Job binary internals
====================

Job binary internal objects represent data processing applications
and libraries that are stored in the internal database.


Create job binary internal
==========================

.. rest_method::  PUT /v1.1/{project_id}/job-binary-internals/{name}

Creates a job binary internal.

Job binary internals are objects that represent data processing
applications and libraries that are stored in the internal
database.

Specify the file contents (raw data or script text) in the request
body. Specify the file name in the URI.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - name: url_job_binary_internals_name


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - name: job_binary_internals_name
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - datasize: datasize
   - id: job_binary_internals_id





Show job binary internal data
=============================

.. rest_method::  GET /v1.1/{project_id}/job-binary-internals/{job_binary_internals_id}/data

Shows data for a job binary internal.

The response body shows the job binary raw data and the response
headers show the data length.

Example response:

::

   HTTP/1.1 200 OK
   Connection: keep-alive
   Content-Length: 161
   Content-Type: text/html; charset=utf-8
   Date: Sat, 28 Mar 2016 02:21:13 GMT
   A = load '$INPUT' using PigStorage(':') as (fruit: chararray);
   B = foreach A generate com.hadoopbook.pig.Trim(fruit);
   store B into '$OUTPUT' USING PigStorage();


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_binary_internals_id: url_job_binary_internals_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - Content-Length: Content-Length



Response Example
----------------

.. literalinclude:: samples/job-binary-internals/show-data-response
   :language: text




Show job binary internal details
================================

.. rest_method::  GET /v1.1/{project_id}/job-binary-internals/{job_binary_internals_id}

Shows details for a job binary internal.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_binary_internals_id: url_job_binary_internals_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - name: job_binary_internals_name
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - datasize: datasize
   - id: job_binary_internals_id



Response Example
----------------

.. literalinclude:: samples/job-binary-internals/show-response.json
   :language: javascript




Delete job binary internal
==========================

.. rest_method::  DELETE /v1.1/{project_id}/job-binary-internals/{job_binary_internals_id}

Deletes a job binary internal.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_binary_internals_id: url_job_binary_internals_id






Update job binary internal
==========================

.. rest_method::  PATCH /v1.1/{project_id}/job-binary-internals/{job_binary_internals_id}

Updates a job binary internal.

Normal respose codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_binary_internals_id: url_job_binary_internals_id

Request Example
---------------

.. literalinclude:: samples/job-binary-internals/update-request.json
   :language: javascript







List job binary internals
=========================

.. rest_method::  GET /v1.1/{project_id}/job-binary-internals

Lists the available job binary internals.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - limit: limit
   - marker: marker
   - sort_by: sort_by_job_binary_internals



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - markers: markers
   - prev: prev
   - next: next
   - binaries: binaries
   - name: job_binary_internals_name
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - datasize: datasize
   - id: job_binary_internals_id



Response Example
----------------
.. rest_method:: GET /v1.1/{project_id}/job-binary-internals

.. literalinclude:: samples/job-binary-internals/list-response.json
   :language: javascript



