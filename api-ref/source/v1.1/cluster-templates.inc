.. -*- rst -*-

=================
Cluster templates
=================

A cluster template configures a Hadoop cluster. A cluster template
lists node groups with the number of instances in each group. You
can also define cluster-scoped configurations in a cluster
template.


Show cluster template details
=============================

.. rest_method::  GET /v1.1/{project_id}/cluster-templates/{cluster_template_id}

Shows details for a cluster template.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_template_id: url_cluster_template_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: cluster_template_description
   - use_autoconfig: use_autoconfig
   - cluster_configs: cluster_configs
   - created_at: created_at
   - default_image_id: default_image_id
   - updated_at: updated_at
   - plugin_name: plugin_name
   - is_default: is_default
   - is_protected: object_is_protected
   - shares: object_shares
   - domain_name: domain_name
   - tenant_id: tenant_id
   - node_groups: node_groups
   - is_public: object_is_public
   - hadoop_version: hadoop_version
   - id: cluster_template_id
   - name: cluster_template_name



Response Example
----------------

.. literalinclude:: samples/cluster-templates/cluster-templates-list-response.json
   :language: javascript




Update cluster templates
========================

.. rest_method::  PUT /v1.1/{project_id}/cluster-templates/{cluster_template_id}

Updates a cluster template.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_template_id: cluster_template_id

Request Example
---------------

.. literalinclude:: samples/cluster-templates/cluster-template-update-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: cluster_template_description
   - use_autoconfig: use_autoconfig
   - cluster_configs: cluster_configs
   - created_at: created_at
   - default_image_id: default_image_id
   - updated_at: updated_at
   - plugin_name: plugin_name
   - is_default: is_default
   - is_protected: object_is_protected
   - shares: object_shares
   - domain_name: domain_name
   - tenant_id: tenant_id
   - node_groups: node_groups
   - is_public: object_is_public
   - hadoop_version: hadoop_version
   - id: cluster_template_id
   - name: cluster_template_name





Delete cluster template
=======================

.. rest_method::  DELETE /v1.1/{project_id}/cluster-templates/{cluster_template_id}

Deletes a cluster template.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_template_id: cluster_template_id






List cluster templates
======================

.. rest_method::  GET /v1.1/{project_id}/cluster-templates

Lists available cluster templates.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - limit: limit
   - marker: marker
   - sort_by: sort_by_cluster_templates

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - markers: markers
   - prev: prev
   - next: next
   - description: cluster_template_description
   - use_autoconfig: use_autoconfig
   - cluster_configs: cluster_configs
   - created_at: created_at
   - default_image_id: default_image_id
   - updated_at: updated_at
   - plugin_name: plugin_name
   - is_default: is_default
   - is_protected: object_is_protected
   - shares: object_shares
   - domain_name: domain_name
   - tenant_id: tenant_id
   - node_groups: node_groups
   - is_public: object_is_public
   - hadoop_version: hadoop_version
   - id: cluster_template_id
   - name: cluster_template_name



Response Example
----------------
.. rest_method:: GET /v1.1/{project_id}/cluster-templates?limit=2

.. literalinclude:: samples/cluster-templates/cluster-templates-list-response.json
   :language: javascript




Create cluster templates
========================

.. rest_method::  POST /v1.1/{project_id}/cluster-templates

Creates a cluster template.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: project_id


Request Example
---------------

.. literalinclude:: samples/cluster-templates/cluster-template-create-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - description: cluster_template_description
   - use_autoconfig: use_autoconfig
   - cluster_configs: cluster_configs
   - created_at: created_at
   - default_image_id: default_image_id
   - updated_at: updated_at
   - plugin_name: plugin_name
   - is_default: is_default
   - is_protected: object_is_protected
   - shares: object_shares
   - domain_name: domain_name
   - tenant_id: tenant_id
   - node_groups: node_groups
   - is_public: object_is_public
   - hadoop_version: hadoop_version
   - id: cluster_template_id
   - name: cluster_template_name




