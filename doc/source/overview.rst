Rationale
=========

Introduction
------------

Apache Hadoop is an industry standard and widely adopted MapReduce implementation.
The aim of this project is to enable users to easily provision and manage Hadoop clusters on OpenStack.
It is worth mentioning that Amazon provides Hadoop for several years as Amazon Elastic MapReduce (EMR) service.

Sahara aims to provide users with simple means to provision Hadoop clusters
by specifying several parameters like Hadoop version, cluster topology, nodes hardware details
and a few more. After user fills in all the parameters, Sahara deploys the cluster in a few minutes.
Also Sahara provides means to scale already provisioned cluster by adding/removing worker nodes on demand.

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

Details
-------

The Sahara product communicates with the following OpenStack components:

* Horizon - provides GUI with ability to use all of Sahara’s features.
* Keystone - authenticates users and provides security token that is used to work with the OpenStack,
  hence limiting user abilities in Sahara to his OpenStack privileges.
* Nova - is used to provision VMs for Hadoop Cluster.
* Heat - Sahara can be configured to use Heat; Heat orchestrates the required services for Hadoop Cluster.
* Glance - Hadoop VM images are stored there, each image containing an installed OS and Hadoop.
  the pre-installed Hadoop should give us good handicap on node start-up.
* Swift - can be used as a storage for data that will be processed by Hadoop jobs.
* Cinder - can be used as a block storage.
* Neutron - provides the networking service.
* Ceilometer - used to collect measures of cluster usage for metering and monitoring purposes.

.. image:: images/openstack-interop.png
    :width: 800 px
    :scale: 99 %
    :align: left

General Workflow
----------------

Sahara will provide two level of abstraction for API and UI based on the addressed use cases:
cluster provisioning and analytics as a service.

For the fast cluster provisioning generic workflow will be as following:

* select Hadoop version;
* select base image with or without pre-installed Hadoop:

    * for base images without Hadoop pre-installed Sahara will support pluggable deployment engines integrated with vendor tooling;

* define cluster configuration, including size and topology of the cluster and setting the different type of Hadoop parameters (e.g. heap size):

    * to ease the configuration of such parameters mechanism of configurable templates will be provided;

* provision the cluster: Sahara will provision VMs, install and configure Hadoop;
* operation on the cluster: add/remove nodes;
* terminate the cluster when it’s not needed anymore.

For analytic as a service generic workflow will be as following:

* select one of predefined Hadoop versions;
* configure the job:

    * choose type of the job: pig, hive, jar-file, etc.;
    * provide the job script source or jar location;
    * select input and output data location (initially only Swift will be supported);
    * select location for logs;

* set limit for the cluster size;
* execute the job:

    * all cluster provisioning and job execution will happen transparently to the user;
    * cluster will be removed automatically after job completion;

* get the results of computations (for example, from Swift).

User's Perspective
------------------

While provisioning cluster through Sahara, user operates on three types of entities: Node Group Templates, Cluster Templates and Clusters.

A Node Group Template describes a group of nodes within cluster. It contains a list of hadoop processes that will be launched on each instance in a group.
Also a Node Group Template may provide node scoped configurations for those processes.
This kind of templates encapsulates hardware parameters (flavor) for the node VM and configuration for Hadoop processes running on the node.

A Cluster Template is designed to bring Node Group Templates together to form a Cluster.
A Cluster Template defines what Node Groups will be included and how many instances will be created in each.
Some of Hadoop Configurations can not be applied to a single node, but to a whole Cluster, so user can specify this kind of configurations in a Cluster Template.
Sahara enables user to specify which processes should be added to an anti-affinity group within a Cluster Template. If a process is included into an anti-affinity
group, it means that VMs where this process is going to be launched should be scheduled to different hardware hosts.

The Cluster entity represents a Hadoop Cluster. It is mainly characterized by VM image with pre-installed Hadoop which
will be used for cluster deployment. User may choose one of pre-configured Cluster Templates to start a Cluster.
To get access to VMs after a Cluster has started, user should specify a keypair.

Sahara provides several constraints on Hadoop cluster topology. JobTracker and NameNode processes could be run either on a single
VM or two separate ones. Also cluster could contain worker nodes of different types. Worker nodes could run both TaskTracker and DataNode,
or either of these processes alone. Sahara allows user to create cluster with any combination of these options,
but it will not allow to create a non working topology, for example: a set of workers with DataNodes, but without a NameNode.

Each Cluster belongs to some tenant determined by user. Users have access only to objects located in
tenants they have access to. Users could edit/delete only objects they created. Naturally admin users have full access to every object.
That way Sahara complies with general OpenStack access policy.

Integration with Swift
----------------------

The Swift service is a standard object storage in OpenStack environment, analog of Amazon S3. As a rule it is deployed
on bare metal machines. It is natural to expect Hadoop on OpenStack to process data stored there. There are a couple
of enhancements on the way which can help there.

First, a FileSystem implementation for Swift: `HADOOP-8545 <https://issues.apache.org/jira/browse/HADOOP-8545>`_.
With that thing in place, Hadoop jobs can work with Swift
as naturally as with HDFS.

On the Swift side, we have the change request: `Change I6b1ba25b <https://review.openstack.org/#/c/21015/>`_ (merged).
It implements the ability to list endpoints for an object, account or container, to make it possible to integrate swift
with software that relies on data locality information to avoid network overhead.

To get more information on how to enable Swift support see :doc:`userdoc/hadoop-swift`.

Pluggable Deployment and Monitoring
-----------------------------------

In addition to the monitoring capabilities provided by vendor-specific Hadoop management tooling, Sahara will provide pluggable integration with external monitoring systems such as Nagios or Zabbix.

Both deployment and monitoring tools will be installed on stand-alone VMs, thus allowing a single instance to manage/monitor several clusters at once.
