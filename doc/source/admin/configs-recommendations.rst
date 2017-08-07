:orphan:

Autoconfiguring templates
=========================

During the Liberty development cycle sahara implemented a tool that recommends
and applies configuration values for cluster templates and node group
templates. These recommendations are based on the number of specific instances
and on flavors of the cluster node groups. Currently the following plugins
support this feature:

  * CDH;
  * Ambari;
  * Spark;
  * the Vanilla Apache Hadoop plugin.

By default this feature is enabled for all cluster templates and node group
templates. If you want to disable this feature for a particular cluster or
node group template you should set the ``use_autoconfig`` field to ``false``.

.. NOTE
  Also, if you manually set configs from the list below, the recommended
  configs will not be applied.

The following describes the settings for which sahara can recommend
autoconfiguration:

The Cloudera, Spark and Vanilla Apache Hadoop plugin support configuring
``dfs.replication`` (``dfs_replication`` for Cloudera plugin) which is
calculated as a minimum from the amount of ``datanode`` (``HDFS_DATANODE`` for
Cloudera plugin) instances in the cluster and the default value for
``dfs.replication``.

The Vanilla Apache Hadoop plugin and Cloudera plugin support autoconfiguration
of basic YARN and MapReduce configs. These autoconfigurations are based on the
following documentation:
http://docs.hortonworks.com/HDPDocuments/HDP2/HDP-2.0.9.1/bk_installing_manually_book/content/rpm-chap1-11.html

The Ambari plugin has its own strategies on configuration recommendations. You
can choose one of ``ALWAYS_APPLY``, ``NEVER_APPLY``, and
``ONLY_STACK_DEFAULTS_APPLY``. By default the Ambari plugin follows the
``NEVER_APPLY`` strategy. You can get more information about strategies in
Ambari's official documentation:
https://cwiki.apache.org/confluence/display/AMBARI/Blueprints#Blueprints-ClusterCreationTemplateStructure
