.. -*- rst -*-

==============
Job executions
==============

A job execution object represents a Hadoop job that runs on a
cluster. A job execution polls the status of a running job and
reports it to the user. Also a user can cancel a running job.


Refresh job execution status
============================

.. rest_method::  GET /v1.1/{project_id}/job-executions/{job_execution_id}/refresh-status

Refreshes the status of and shows information for a job execution.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_execution_id: url_job_execution_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_id: job_id
   - updated_at: updated_at
   - tenant_id: tenant_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_execution_is_public
   - input_id: input_id
   - configs: configs
   - job_execution: job_execution
   - id: job_execution_id



Response Example
----------------

.. literalinclude:: samples/job-executions/job-ex-response.json
   :language: javascript




List job executions
===================

.. rest_method::  GET /v1.1/{project_id}/job-executions

Lists available job executions.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - limit: limit
   - marker: marker
   - sort_by: sort_by_job_execution



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - markers: markers
   - prev: prev
   - next: next
   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_id: job_id
   - updated_at: updated_at
   - tenant_id: tenant_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_execution_is_public
   - input_id: input_id
   - configs: configs
   - job_execution: job_execution
   - id: job_execution_id
   - job_executions: job_executions



Response Example
----------------
.. rest_method:: /v1.1/{project_id}/job-executions

.. literalinclude:: samples/job-executions/list-response.json
   :language: javascript




Show job execution details
==========================

.. rest_method::  GET /v1.1/{project_id}/job-executions/{job_execution_id}

Shows details for a job execution, by ID.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_execution_id: url_job_execution_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_id: job_id
   - updated_at: updated_at
   - tenant_id: tenant_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_execution_is_public
   - input_id: input_id
   - configs: configs
   - job_execution: job_execution
   - id: job_execution_id



Response Example
----------------

.. literalinclude:: samples/job-executions/job-ex-response.json
   :language: javascript




Delete job execution
====================

.. rest_method::  DELETE /v1.1/{project_id}/job-executions/{job_execution_id}

Deletes a job execution.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_execution_id: url_job_execution_id






Update job execution
====================

.. rest_method::  PATCH /v1.1/{project_id}/job-executions/{job_execution_id}

Updates a job execution.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_execution_id: url_job_execution_id

Request Example
---------------

.. literalinclude:: samples/job-executions/job-ex-update-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_id: job_id
   - updated_at: updated_at
   - tenant_id: tenant_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_execution_is_public
   - input_id: input_id
   - configs: configs
   - job_execution: job_execution
   - id: job_execution_id





Cancel job execution
====================

.. rest_method::  GET /v1.1/{project_id}/job-executions/{job_execution_id}/cancel

Cancels a job execution.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - job_execution_id: url_job_execution_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - info: info
   - output_id: output_id
   - start_time: start_time
   - job_id: job_id
   - updated_at: updated_at
   - tenant_id: tenant_id
   - created_at: created_at
   - args: args
   - data_source_urls: data_source_urls
   - return_code: return_code
   - oozie_job_id: oozie_job_id
   - is_protected: is_protected_3
   - cluster_id: cluster_id
   - end_time: end_time
   - params: params
   - is_public: job_execution_is_public
   - input_id: input_id
   - configs: configs
   - job_execution: job_execution
   - id: job_execution_id



Response Example
----------------

.. literalinclude:: samples/job-executions/cancel-response.json
   :language: javascript



