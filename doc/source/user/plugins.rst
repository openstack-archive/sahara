Provisioning Plugins
====================

This page lists all available provisioning plugins. In general a plugin
enables sahara to deploy a specific data processing framework (for example,
Hadoop) or distribution, and allows configuration of topology and
management/monitoring tools.

The plugins currently developed as part of the official Sahara project are:

* :sahara-plugin-ambari-doc:`Ambari Plugin <>` -
  deploys Hortonworks Data Platform
* :sahara-plugin-cdh-doc:`CDH Plugin <>` -
  deploys Cloudera Hadoop
* :sahara-plugin-mapr-doc:`MapR Plugin <>` -
  deploys MapR plugin with MapR File System
* :sahara-plugin-spark-doc:`Spark Plugin <>` -
  deploys Apache Spark with Cloudera HDFS
* :sahara-plugin-storm-doc:`Storm Plugin <>` -
  deploys Apache Storm
* :sahara-plugin-vanilla-doc:`Vanilla Plugin <>` -
  deploys Vanilla Apache Hadoop

Managing plugins
----------------

Since the Newton release a project admin can configure plugins by specifying
additional values for plugin's labels.

To disable a plugin (Vanilla Apache Hadoop, for example), the admin
can run the following command:

.. code-block::

 cat update_configs.json
 {
     "plugin_labels": {
         "enabled": {
             "status": true
         }
     }
 }
 openstack dataprocessing plugin update vanilla update_configs.json


Additionally, specific versions can be disabled by the following command:

.. code-block::

 cat update_configs.json
 {
     "version_labels": {
         "2.7.1": {
             "enabled": {
                 "status": true
             }
         }
     }
 }
 openstack dataprocessing plugin update vanilla update_configs.json


Finally, to see all labels of a specific plugin and to see the current status
of the plugin (is it stable or not, deprecation status) the following command
can be executed from the CLI:

.. code-block::

 openstack dataprocessing plugin show vanilla

The same actions are available from UI respectively.
