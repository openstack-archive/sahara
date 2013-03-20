Savanna Roadmap
===============

Phase 1 - Basic Cluster Provisioning
------------------------------------
completion - early April

* Cluster provisioning
* Deployment Engine implementation for pre-installed images
* Templates for Hadoop cluster configuration
* REST API for cluster startup and operations
* UI integrated into Horizon

Phase 2 - Cluster Operations
----------------------------
completion - end of June

* Manual cluster scaling (add/remove nodes)
* Hadoop cluster topology configuration parameters

    * Data node placement control
    * HDFS location
    * Swift integration

* Integration with vendor specific deployment/management tooling
* Monitoring support - integration with 3rd-party monitoring tools (Zabbix, Nagios)

Phase 3 - Analytics as a Service
--------------------------------
completion - end of September

* API to execute Map/Reduce jobs without exposing details of underlying infrastructure (similar to AWS EMR)
* User-friendly UI for ad-hoc analytics queries based on Hive or Pig

Further Roadmap
---------------
completion - TBD

* HDFS and Swift integration

    * Caching of Swift data on HDFS
    * Avoid issues with Swift eventual consistency while running job

* HBase support

