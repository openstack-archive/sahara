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

.. rest_method::  GET /v1.1/{tenant_id}/data-sources/{data_source_id}

Shows details for a data source.


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - data_source_id: data_source_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: is_protected
   - is_public: is_public
   - type: type
   - id: id
   - name: name



Response Example
----------------

.. literalinclude:: samples/data-sources/data-source-show-response.json
   :language: javascript




Delete data source
==================

.. rest_method::  DELETE /v1.1/{tenant_id}/data-sources/{data_source_id}

Deletes a data source.

Error response codes:204,


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - data_source_id: data_source_id






Update data source
==================

.. rest_method::  PUT /v1.1/{tenant_id}/data-sources/{data_source_id}

Updates a data source.

Error response codes:202,


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id
   - data_source_id: data_source_id

Request Example
---------------

.. literalinclude:: samples/data-sources/data-source-update-request.json
   :language: javascript







List data sources
=================

.. rest_method::  GET /v1.1/{tenant_id}/data-sources

Lists all data sources.


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: is_protected
   - is_public: is_public
   - type: type
   - id: id
   - name: name



Response Example
----------------

.. literalinclude:: samples/data-sources/data-sources-list-response.json
   :language: javascript




Create data source
==================

.. rest_method::  POST /v1.1/{tenant_id}/data-sources

Creates a data source.

Error response codes:202,


Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: url_tenant_id


Request Example
---------------

.. literalinclude:: samples/data-sources/data-source-register-hdfs-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: description
   - url: url
   - tenant_id: tenant_id
   - created_at: created_at
   - updated_at: updated_at
   - is_protected: is_protected
   - is_public: is_public
   - type: type
   - id: id
   - name: name




