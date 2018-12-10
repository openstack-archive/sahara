.. -*- rst -*-

=============
Job templates
=============

A job templates object lists the binaries that a job needs to run.
To run a job, you must specify data sources and job parameters.

You can run a job on an existing or new transient cluster.


List job templates
==================

.. rest_method::  GET /v2/job-templates

Lists all job templates.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - limit: limit
   - marker: marker
   - sort_by: sort_by_job_templates



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - job_templates: job_templates
   - description: job_description
   - project_id: project_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: object_is_protected
   - interface: interface
   - is_public: object_is_public
   - type: type
   - id: job_template_id
   - name: job_template_name
   - markers: markers
   - prev: prev
   - next: next


Response Example
----------------
..rest_method:: GET /v2/job-templates?limit=2

.. literalinclude:: samples/job-templates/job-templates-list-response.json
   :language: javascript




Create job template
===================

.. rest_method::  POST /v2/job-templates

Creates a job object.

Normal response codes:202




Request Example
---------------

.. literalinclude:: samples/job-templates/job-template-create-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: job_description
   - project_id: project_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: object_is_protected
   - interface: interface
   - is_public: object_is_public
   - type: type
   - id: job_template_id
   - name: job_template_name





Show job template details
=========================

.. rest_method::  GET /v2/job-templates/{job_template_id}

Shows details for a job template.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - job_template_id: url_job_template_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: job_description
   - project_id: project_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: object_is_protected
   - interface: interface
   - is_public: object_is_public
   - type: type
   - id: job_template_id
   - name: job_template_name



Response Example
----------------

.. literalinclude:: samples/job-templates/job-template-show-response.json
   :language: javascript




Remove job template
===================

.. rest_method::  DELETE /v2/job-templates/{job_template_id}

Removes a job.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - job_template_id: url_job_template_id






Update job template object
==========================

.. rest_method::  PATCH /v2/job-templates/{job_template_id}

Updates a job template object.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - job_template_id: url_job_template_id

Request Example
---------------

.. literalinclude:: samples/job-templates/job-template-update-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: job_description
   - project_id: project_id
   - created_at: created_at
   - mains: mains
   - updated_at: updated_at
   - libs: libs
   - is_protected: object_is_protected
   - interface: interface
   - is_public: object_is_public
   - type: type
   - id: job_template_id
   - name: job_template_name





Get job template config hints
=============================

.. rest_method::  GET /v2/job-templates/config-hints/{job_type}

Get job template config hints

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - job_type: url_job_type


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - job_config: job_config
   - args: args
   - configs: configs





