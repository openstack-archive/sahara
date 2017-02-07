.. -*- rst -*-

========
Clusters
========

A cluster is a group of nodes with the same configuration.


List available clusters
=======================

.. rest_method::  GET /v1.1/{project_id}/clusters

Lists available clusters.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - limit: limit
   - marker: marker
   - sort_by: sort_by_clusters



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - markers: markers
   - prev: prev
   - next: next
   - count: count
   - info: info
   - cluster_template_id: cluster_template_id
   - is_transient: is_transient
   - provision_progress: provision_progress
   - status: status
   - neutron_management_network: neutron_management_network
   - clusters: clusters
   - management_public_key: management_public_key
   - status_description: status_description
   - trust_id: trust_id
   - domain_name: domain_name



Response Example
----------------
.. rest_method:: GET /v1.1/{project_id}/clusters

.. literalinclude:: samples/clusters/clusters-list-response.json
   :language: javascript




Create cluster
==============

.. rest_method::  POST /v1.1/{project_id}/clusters

Creates a cluster.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id


Request Example
---------------

.. literalinclude:: samples/clusters/cluster-create-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - count: count
   - info: info
   - cluster_template_id: cluster_template_id
   - is_transient: is_transient
   - provision_progress: provision_progress
   - status: status
   - neutron_management_network: neutron_management_network
   - management_public_key: management_public_key
   - status_description: status_description
   - trust_id: trust_id
   - domain_name: domain_name





Create multiple clusters
========================

.. rest_method::  POST /v1.1/{project_id}/clusters/multiple

Creates multiple clusters.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id


Request Example
---------------

.. literalinclude:: samples/clusters/multiple-clusters-create-request.json
   :language: javascript







Show details of a cluster
=========================

.. rest_method::  GET /v1.1/{project_id}/clusters/{cluster_id}

Shows details for a cluster, by ID.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_id: url_cluster_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - count: count
   - info: info
   - cluster_template_id: cluster_template_id
   - is_transient: is_transient
   - provision_progress: provision_progress
   - status: status
   - neutron_management_network: neutron_management_network
   - management_public_key: management_public_key
   - status_description: status_description
   - trust_id: trust_id
   - domain_name: domain_name



Response Example
----------------

.. literalinclude:: samples/clusters/cluster-show-response.json
   :language: javascript




Delete a cluster
================

.. rest_method::  DELETE /v1.1/{project_id}/clusters/{cluster_id}

Deletes a cluster.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_id: url_cluster_id






Scale cluster
=============

.. rest_method::  PUT /v1.1/{project_id}/clusters/{cluster_id}

Scales a cluster.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_id: cluster_id

Request Example
---------------

.. literalinclude:: samples/clusters/cluster-scale-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - count: count
   - info: info
   - cluster_template_id: cluster_template_id
   - is_transient: is_transient
   - provision_progress: provision_progress
   - status: status
   - neutron_management_network: neutron_management_network
   - management_public_key: management_public_key
   - status_description: status_description
   - trust_id: trust_id
   - domain_name: domain_name




Update cluster
==============

.. rest_method::  PATCH /v1.1/{project_id}/clusters/{cluster_id}

Updates a cluster.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_id: url_cluster_id

Request Example
---------------

.. literalinclude:: samples/clusters/cluster-update-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - count: count
   - info: info
   - cluster_template_id: cluster_template_id
   - is_transient: is_transient
   - provision_progress: provision_progress
   - status: status
   - neutron_management_network: neutron_management_network
   - management_public_key: management_public_key
   - status_description: status_description
   - trust_id: trust_id
   - domain_name: domain_name




Show progress
=============

.. rest_method::  GET /v1.1/{project_id}/clusters/{cluster_id}

Shows provisioning progress for a cluster.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_id: url_cluster_id




Response Example
----------------

.. literalinclude:: samples/event-log/cluster-progress-response.json
   :language: javascript



