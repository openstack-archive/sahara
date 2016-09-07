.. -*- rst -*-

====
Jobs
====

A job object lists the binaries that a job needs to run. To run a
job, you must specify data sources and job parameters.

You can run a job on an existing or new transient cluster.


Run job
=======

.. rest_method::  POST /v1.1/{tenant_id}/jobs/{job_id}/execute

Runs a job.

Error response codes:202,


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - job_id: job_id

Request Example
---------------

.. literalinclude:: samples/jobs/job-execute-request.json
   :language: javascript







List jobs
=========

.. rest_method::  GET /v1.1/{tenant_id}/jobs

Lists all jobs.


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - limit: limit
   - marker: marker
   - sort_by: sort_by_jobs



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - jobs: jobs
   - description: description
   - tenant_id: tenant_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: is_protected
   - interface: interface
   - is_public: is_public
   - type: type
   - id: id
   - name: name
   - markers: markers
   - prev: prev
   - next: next


Response Example
----------------
..rest_method:: GET /v1.1/{tenant_id}/jobs?limit=2

.. literalinclude:: samples/jobs/jobs-list-response.json
   :language: javascript




Create job
==========

.. rest_method::  POST /v1.1/{tenant_id}/jobs

Creates a job object.

Error response codes:202,


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id


Request Example
---------------

.. literalinclude:: samples/jobs/job-create-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - tenant_id: tenant_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: is_protected
   - interface: interface
   - is_public: is_public
   - type: type
   - id: id
   - name: name





Show job details
================

.. rest_method::  GET /v1.1/{tenant_id}/jobs/{job_id}

Shows details for a job.


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - job_id: job_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - tenant_id: tenant_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: is_protected
   - interface: interface
   - is_public: is_public
   - type: type
   - id: id
   - name: name



Response Example
----------------

.. literalinclude:: samples/jobs/job-show-response.json
   :language: javascript




Remove job
==========

.. rest_method::  DELETE /v1.1/{tenant_id}/jobs/{job_id}

Removes a job.

Error response codes:204,


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - job_id: job_id






Update job object
=================

.. rest_method::  PATCH /v1.1/{tenant_id}/jobs/{job_id}

Updates a job object.

Error response codes:202,


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - job_id: job_id

Request Example
---------------

.. literalinclude:: samples/jobs/job-update-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - tenant_id: tenant_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: is_protected
   - interface: interface
   - is_public: is_public
   - type: type
   - id: id
   - name: name




