Apache Hadoop Configurations for Sahara
========================================

This directory contains default XML configuration files:

* core-default.xml,
* hdfs-default.xml,
* mapred-default.xml,
* yarn-default.xml

These files are applied for Sahara's plugin of Apache Hadoop version 2.3.0


Files were taken from here:
https://github.com/apache/hadoop-common/blob/release-2.3.0/hadoop-common-project/hadoop-common/src/main/resources/core-default.xml
https://github.com/apache/hadoop-common/blob/release-2.3.0/hadoop-hdfs-project/hadoop-hdfs/src/main/resources/hdfs-default.xml
https://github.com/apache/hadoop-common/blob/release-2.3.0/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-common/src/main/resources/yarn-default.xml
https://github.com/apache/hadoop-common/blob/release-2.3.0/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-core/src/main/resources/mapred-default.xml

XML configs are used to expose default Hadoop configurations to the users through
Sahara's REST API. It allows users to override some config values which will
be pushed to the provisioned VMs running Hadoop services as part of appropriate
xml config.
