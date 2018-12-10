.. -*- rst -*-

====
Jobs
====

A job object represents a job that runs on a cluster.
A job polls the status of a running job and reports it to the user.


Execute Job
===========

.. rest_method::  POST /v2/jobs

Executes a job.


Normal response codes: 200

Request Example
----------------
.. rest_method:: /v2/jobs

.. literalinclude:: samples/jobs/job-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_template_id: job_template_id
   - updated_at: updated_at
   - project_id: project_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_is_public
   - input_id: input_id
   - configs: configs
   - job: job
   - id: job_id



Response Example
----------------

.. literalinclude:: samples/jobs/job-response.json
   :language: javascript




List jobs
=========

.. rest_method::  GET /v2/jobs

Lists available jobs.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - limit: limit
   - marker: marker
   - sort_by: sort_by_job



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - markers: markers
   - prev: prev
   - next: next
   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_template_id: job_template_id
   - updated_at: updated_at
   - project_id: project_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_is_public
   - input_id: input_id
   - configs: configs
   - job: job
   - id: job_id
   - jobs: jobs



Response Example
----------------
.. rest_method:: /v2/jobs

.. literalinclude:: samples/jobs/list-response.json
   :language: javascript




Show job
========

.. rest_method::  GET /v2/jobs/{job_id}

Shows details for a job, by ID.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - job_id: url_job_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_template_id: job_template_id
   - updated_at: updated_at
   - project_id: project_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_is_public
   - input_id: input_id
   - configs: configs
   - job: job
   - id: job_id



Response Example
----------------

.. literalinclude:: samples/jobs/job-response.json
   :language: javascript




Delete job
==========

.. rest_method::  DELETE /v2/jobs/{job_id}

Deletes a job.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - job_id: url_job_id






Update job
==========

.. rest_method::  PATCH /v2/jobs/{job_id}

Updates a job.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - job_id: url_job_id

Request Example
---------------

.. literalinclude:: samples/jobs/job-update-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_template_id: job_template_id
   - updated_at: updated_at
   - project_id: project_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_is_public
   - input_id: input_id
   - configs: configs
   - job: job
   - id: job_id





