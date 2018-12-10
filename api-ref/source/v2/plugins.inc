.. -*- rst -*-

=======
Plugins
=======

A plugin object defines the Hadoop or Spark version that it can
install and which configurations can be set for the cluster.


Show plugin details
===================

.. rest_method::  GET /v2/plugins/{plugin_name}

Shows details for a plugin.


Normal response codes: 200
Error response codes: 400, 500


Request
-------

.. rest_parameters:: parameters.yaml

   - plugin_name: url_plugin_name


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - versions: versions
   - title: title
   - description: description_plugin
   - name: plugin_name



Response Example
----------------

.. literalinclude:: samples/plugins/plugin-show-response.json
   :language: javascript




List plugins
============

.. rest_method::  GET /v2/plugins

Lists all registered plugins.


Normal response codes: 200
Error response codes: 400, 500





Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - title: title
   - versions: versions
   - plugins: plugins
   - description: description_plugin
   - name: plugin_name



Response Example
----------------

.. literalinclude:: samples/plugins/plugins-list-response.json
   :language: javascript




Show plugin version details
===========================

.. rest_method::  GET /v2/plugins/{plugin_name}/{version}

Shows details for a plugin version.


Normal response codes: 200
Error response codes: 400, 500


Request
-------

.. rest_parameters:: parameters.yaml

   - plugin_name: url_plugin_name
   - version: version


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - versions: versions
   - title: title
   - description: description_plugin
   - name: plugin_name



Response Example
----------------

.. literalinclude:: samples/plugins/plugin-version-show-response.json
   :language: javascript




Update plugin details
=====================

.. rest_method::  PATCH /v2/plugins/{plugin_name}

Updates details for a plugin.


Normal response codes: 202
Error response codes: 400, 500


Request
-------

.. rest_parameters:: parameters.yaml

   - plugin_name: url_plugin_name


Request Example
---------------

.. literalinclude:: samples/plugins/plugin-update-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - title: title
   - versions: versions
   - description: description_plugin
   - name: plugin_name


Response Example
----------------

.. literalinclude:: samples/plugins/plugin-update-response.json
   :language: javascript





