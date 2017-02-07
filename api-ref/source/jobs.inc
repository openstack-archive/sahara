.. -*- rst -*-

====
Jobs
====

A job object lists the binaries that a job needs to run. To run a
job, you must specify data sources and job parameters.

You can run a job on an existing or new transient cluster.


Run job
=======

.. rest_method::  POST /v1.1/{project_id}/jobs/{job_id}/execute

Runs a job.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_id: url_job_id

Request Example
---------------

.. literalinclude:: samples/jobs/job-execute-request.json
   :language: javascript







List jobs
=========

.. rest_method::  GET /v1.1/{project_id}/jobs

Lists all jobs.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - limit: limit
   - marker: marker
   - sort_by: sort_by_jobs



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - jobs: jobs
   - description: job_description
   - tenant_id: tenant_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: object_is_protected
   - interface: interface
   - is_public: object_is_public
   - type: type
   - id: job_id
   - name: job_name
   - markers: markers
   - prev: prev
   - next: next


Response Example
----------------
..rest_method:: GET /v1.1/{project_id}/jobs?limit=2

.. literalinclude:: samples/jobs/jobs-list-response.json
   :language: javascript




Create job
==========

.. rest_method::  POST /v1.1/{project_id}/jobs

Creates a job object.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id


Request Example
---------------

.. literalinclude:: samples/jobs/job-create-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: job_description
   - tenant_id: tenant_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: object_is_protected
   - interface: interface
   - is_public: object_is_public
   - type: type
   - id: job_id
   - name: job_name





Show job details
================

.. rest_method::  GET /v1.1/{project_id}/jobs/{job_id}

Shows details for a job.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_id: url_job_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: job_description
   - tenant_id: tenant_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: object_is_protected
   - interface: interface
   - is_public: object_is_public
   - type: type
   - id: job_id
   - name: job_name



Response Example
----------------

.. literalinclude:: samples/jobs/job-show-response.json
   :language: javascript




Remove job
==========

.. rest_method::  DELETE /v1.1/{project_id}/jobs/{job_id}

Removes a job.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_id: url_job_id






Update job object
=================

.. rest_method::  PATCH /v1.1/{project_id}/jobs/{job_id}

Updates a job object.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_id: url_job_id

Request Example
---------------

.. literalinclude:: samples/jobs/job-update-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: job_description
   - tenant_id: tenant_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: object_is_protected
   - interface: interface
   - is_public: object_is_public
   - type: type
   - id: job_id
   - name: job_name




