.. -*- rst -*-

=========
Event log
=========

The event log feature provides information about cluster
provisioning. In the event of errors, the event log shows the
reason for the failure.


Show progress
=============

.. rest_method::  GET /v1.1/{project_id}/clusters/{cluster_id}

Shows provisioning progress of cluster.


Normal response codes: 200
Error response codes:


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - cluster_id: cluster_id




Response Example
----------------

.. literalinclude:: samples/event-log/cluster-progress-response.json
   :language: javascript



