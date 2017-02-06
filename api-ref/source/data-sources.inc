.. -*- rst -*-

============
Data sources
============

A data source object defines the location of input or output for
MapReduce jobs and might reference different types of storage.

The Data Processing service does not validate data source
locations.


Show data source details
========================

.. rest_method::  GET /v1.1/{project_id}/data-sources/{data_source_id}

Shows details for a data source.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - data_source_id: url_data_source_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: data_source_description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - type: type
   - id: data_source_id
   - name: data_source_name



Response Example
----------------

.. literalinclude:: samples/data-sources/data-source-show-response.json
   :language: javascript




Delete data source
==================

.. rest_method::  DELETE /v1.1/{project_id}/data-sources/{data_source_id}

Deletes a data source.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - data_source_id: url_data_source_id






Update data source
==================

.. rest_method::  PUT /v1.1/{project_id}/data-sources/{data_source_id}

Updates a data source.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - data_source_id: url_data_source_id

Request Example
---------------

.. literalinclude:: samples/data-sources/data-source-update-request.json
   :language: javascript







List data sources
=================

.. rest_method::  GET /v1.1/{project_id}/data-sources

Lists all data sources.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - limit: limit
   - marker: marker
   - sort_by: sort_by_data_sources


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - markers: markers
   - prev: prev
   - next: next
   - description: data_source_description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - type: type
   - id: data_source_id
   - name: data_source_name



Response Example
----------------

.. rest_method:: GET /v1.1/{project_id}/data-sourses?sort_by=-name

.. literalinclude:: samples/data-sources/data-sources-list-response.json
   :language: javascript




Create data source
==================

.. rest_method::  POST /v1.1/{project_id}/data-sources

Creates a data source.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id


Request Example
---------------

.. literalinclude:: samples/data-sources/data-source-register-hdfs-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: data_source_description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - type: type
   - id: data_source_id
   - name: data_source_name




