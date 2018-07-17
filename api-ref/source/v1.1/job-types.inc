.. -*- rst -*-

=========
Job types
=========

Each plugin that supports EDP also supports specific job types.
Different versions of a plugin might actually support different job
types. Configuration options vary by plugin, version, and job type.

The job types provide information about which plugins support which
job types and how to configure the job types.


List job types
==============

.. rest_method::  GET /v1.1/{project_id}/job-types

Lists all job types.

You can use query parameters to filter the response.


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - plugin: plugin
   - version: version
   - type: type
   - hints: hints


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - versions: versions
   - title: title
   - description: description_plugin
   - job_types: job_types
   - name: plugin_name



Response Example
----------------

.. literalinclude:: samples/job-types/job-types-list-response.json
   :language: javascript



