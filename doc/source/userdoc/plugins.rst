Provisioning Plugins
====================

This page lists all available provisioning plugins. In general a plugin
enables sahara to deploy a specific data processing framework (for example,
Hadoop) or distribution, and allows configuration of topology and
management/monitoring tools.

* :doc:`vanilla_plugin` - deploys Vanilla Apache Hadoop
* :doc:`ambari_plugin` - deploys Hortonworks Data Platform
* :doc:`spark_plugin` - deploys Apache Spark with Cloudera HDFS
* :doc:`mapr_plugin` - deploys MapR plugin with MapR File System
* :doc:`cdh_plugin` - deploys Cloudera Hadoop

Managing plugins
----------------

Since the Newton release a project admin can configure plugins by specifying
additional values for plugin's labels.

To disable a plugin (Vanilla Apache Hadoop, for example), the admin
can run the following command:

.. sourcecode:: console

 cat update_configs.json
 {
     "plugin_labels": {
         "enabled": {
             "status": true
         }
     }
 }
 openstack plugin update vanilla update_configs.json


Additionally, specific versions can be disabled by the following command:

.. sourcecode:: console

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
 openstack plugin update vanilla update_configs.json


Finally, to see all labels of a specific plugin and to see the current status
of the plugin (is it stable or not, deprecation status) the following command
can be executed from the CLI:

.. sourcecode:: console

 openstack plugin show vanilla

The same actions are available from UI respectively.
