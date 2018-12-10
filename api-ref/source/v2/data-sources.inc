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

.. rest_method::  GET /v2/data-sources/{data_source_id}

Shows details for a data source.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - data_source_id: url_data_source_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: data_source_description
   - url: url
   - project_id: project_id
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

.. rest_method::  DELETE /v2/data-sources/{data_source_id}

Deletes a data source.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - data_source_id: url_data_source_id






Update data source
==================

.. rest_method::  PATCH /v2/data-sources/{data_source_id}

Updates a data source.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - data_source_id: url_data_source_id

Request Example
---------------

.. literalinclude:: samples/data-sources/data-source-update-request.json
   :language: javascript







List data sources
=================

.. rest_method::  GET /v2/data-sources

Lists all data sources.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

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
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - type: type
   - id: data_source_id
   - name: data_source_name



Response Example
----------------

.. rest_method:: GET /v2/data-sourses?sort_by=-name

.. literalinclude:: samples/data-sources/data-sources-list-response.json
   :language: javascript




Create data source
==================

.. rest_method::  POST /v2/data-sources

Creates a data source.

Normal response codes:202



Request Example
---------------

.. literalinclude:: samples/data-sources/data-source-register-hdfs-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: data_source_description
   - url: url
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: object_is_protected
   - is_public: object_is_public
   - type: type
   - id: data_source_id
   - name: data_source_name





