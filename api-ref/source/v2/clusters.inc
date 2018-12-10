.. -*- rst -*-

========
Clusters
========

A cluster is a group of nodes with the same configuration.


List available clusters
=======================

.. rest_method::  GET /v2/clusters

Lists available clusters.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

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
.. rest_method:: GET /v2/clusters

.. literalinclude:: samples/clusters/clusters-list-response.json
   :language: javascript




Create cluster
==============

.. rest_method::  POST /v2/clusters

Creates a cluster.

Normal response codes: 202



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





Show details of a cluster
=========================

.. rest_method::  GET /v2/clusters/{cluster_id}

Shows details for a cluster, by ID.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

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

.. rest_method::  DELETE /v2/clusters/{cluster_id}

Deletes a cluster.

Normal response codes: 204 or 200


Request
-------

.. rest_parameters:: parameters.yaml

   - cluster_id: url_cluster_id
   - force: force






Scale cluster
=============

.. rest_method::  PUT /v2/clusters/{cluster_id}

Scales a cluster.

Normal response codes: 202


Request
-------

.. rest_parameters:: parameters.yaml

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

.. rest_method::  PATCH /v2/clusters/{cluster_id}

Updates a cluster.

Normal response codes: 202


Request
-------

.. rest_parameters:: parameters.yaml

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

.. rest_method::  GET /v2/clusters/{cluster_id}

Shows provisioning progress for a cluster.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - cluster_id: url_cluster_id




Response Example
----------------

.. literalinclude:: samples/event-log/cluster-progress-response.json
   :language: javascript



