Introduction
------------

Apache Hadoop is an industry standard and widely adopted MapReduce implementation.
The aim of this project is to enable users to easily provision and manage Hadoop clusters on OpenStack.
It is worth mentioning that Amazon provides Hadoop for several years as Amazon Elastic MapReduce (EMR) service.

Savanna aims to provide users with simple means to provision Hadoop clusters
by specifying several parameters like Hadoop version, cluster topology, nodes hardware details
and a few more. After user fills in all the parameters, Savanna deploys the cluster in a few minutes.
Also Savanna provides means to scale already provisioned cluster by adding/removing worker nodes on demand.

The solution will address following use cases:

* fast provisioning of Hadoop clusters on OpenStack for Dev and QA;
* utilization of unused compute power from general purpose OpenStack IaaS cloud;
* "Analytics as a Service" for ad-hoc or bursty analytic workloads (similar to AWS EMR).

Key features are:

* designed as an OpenStack component;
* managed through REST API with UI available as part of OpenStack Dashboard;
* support for different Hadoop distributions:
    * pluggable system of Hadoop installation engines;
    * integration with vendor specific management tools, such as Apache Ambari or Cloudera Management Console;
* predefined templates of Hadoop configurations with ability to modify parameters.