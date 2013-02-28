Welcome to Elastic Hadoop on OpenStack documentation!
=====================================================

Introduction
------------

Apache Hadoop is an industry standard and widely adopted MapReduce implementation.
The aim of this project is to enable users to easily provision and manage Hadoop clusters on OpenStack.
It is worth mentioning that Amazon provides Hadoop for several years as Amazon Elastic MapReduce (EMR) service.

EHO aims to provide users with simple means to provision a Hadoop cluster by specifying several parameters
like Hadoop version, cluster topology, nodes hardware details and a few more. After user fills in all the parameters,
EHO deploys the cluster in a few minutes. Also EHO provides means to scale already provisioned cluster by
adding/removing worker nodes on demand.

Fast and simple provision means that EHO will be convenient for deploying Hadoop for various purposes.
For instance, user could quickly create a cluster for experiments, play with it and then kill the cluster without
regret.
At the same time limited user's input and automated provisioning
means that an on-demand cluster could be created for each job, instead of running all jobs on a single permanent
cluster.
That is similar to what Amazon EMR service offers.

EHO is designed to be pluggable framework integrated with existing and widely adopted management solutions
(Apache Ambari, Cloudera Management Console) and supporting various Hadoop versions on different OSes.

EHO will extend OpenStack Dashboard to keep it up as a single endpoint for managing all cloud services.
The ultimate goal of EHO GUI is to provide one-click cluster provisioning and job execution.

The main idea of the project is implementation of MapReduce service for OpenStack similar to Amazon EMR.

Details
-------

The EHO product communicates with the following OpenStack components:

* Horizon - provides GUI with ability to use all of EHO's features

* Keystone - authenticates users and provides security token that is used to work with the OpenStack,
  hence limiting user abilities in EHO to his OpenStack privileges

* Nova - is used to provision VMs for Hadoop Cluster

* Glance - Hadoop VM images are stored there, each image containing an installed OS and Hadoop;
  the pre-installed Hadoop should give us good handicap on node start-up

* Swift - storage for data that will be processed by Hadoop jobs

.. image:: images/openstack-interop.png

General Workflow
----------------

EHO provides several kinds of Hadoop cluster topology. JobTracker and NameNode processes could be run
either on a single VM or two separate ones. Also cluster could contain worker nodes of different types.
Worker nodes could run both TaskTracker and DataNode, or either of these processes alone.
EHO allows user to create cluster with any combination of these options.
It only validates that cluster topology has exactly one JobTracker and one NameNode processes.

EHO is designed to have pluggable deployment mechanism. It allows to provision Hadoop cluster with various approaches,
including existing management/deployment solutions like OpenStack Heat, Apache Ambari and Cloudera Management Console.

A reference implementation will be provided for deployment mechanism which does fast cluster provisioning using
pre-installed Hadoop image. Image is a disk with installed OS and Hadoop, and that gives user an ability to select
both Hadoop and Linux distributions he wishes to use. The implementation has some pre-built images. Also users will
be provided with a guide on how to create custom image in case pre-built ones are not sufficient.

User's Perspective
------------------

While provisioning cluster through EHO, user operates on two types of entities: Node Templates and Clusters.

Node Template describes a node within cluster and it has several parameters. Node type determines which Hadoop
processes will be running on the node and thereby its role in the cluster. It could be either of JobTracker, NameNode,
TaskTracker or DataNode, or any combination of these. Also template encapsulates hardware parameters for the node VM
and configuration for Hadoop processes running on the node.

Cluster simply represents Hadoop Cluster. It is mainly characterized by Hadoop image which will be used for cluster
deployment and cluster topology. The topology is a list of node templates and respectively amount of nodes being
deployed for each template. With respect to topology, EHO checks only that cluster has one JobTracker and one NameNode.

Each node template and cluster belongs to some tenant determined by user. Users have access only to objects located
in tenants they have access to. Users could edit/delete only objects they created. Naturally admin users have full
access to every object. That way EHO complies with general OpenStack access policy.

Integration with Swift
----------------------

The Swift service is a standard file storage in OpenStack environment, analog of Amazon S3. As a rule it is deployed
on bare metal machines. It is natural to expect Hadoop on OpenStack to process data stored there. There are a couple
of enhancements on the way which can help there.

First, a FileSystem implementation for Swift: `HADOOP-8545 <https://issues.apache.org/jira/browse/HADOOP-8545/>`_.
With that thing in place, Hadoop jobs can work with Swift as naturally as with HDFS.

On the Swift side, we have the change request: `Change I6b1ba25b <https://review.openstack.org/#/c/21015/>`_.
It implements the ability to list endpoints for an object, account or container, to make it possible to integrate
swift with software that relies on data locality information to avoid network overhead.

HDFS is not that reliable in virtual environment. Assume the following example: we have HDFS deployed in OpenStack.
If we store a file in HDFS with replication factor 3, it could happen that all 3 replicas of the file will be stored
on VMs running on a single compute node. In that case the node failure will cause file loss.

The problem becomes even more complex if HDFS nodes use external volumes as disks. In that case it could also happen
that all 3 volumes storing file replicas are located on the same cinder node. Similarly, if that node fails,
file is also lost.

Still, it makes sense to deploy data nodes on task tracker VMs. HDFS deployed in such a way could be used to store
intermediate data for a sequence of jobs. Both input of the first job and output of the last one could be reliably
stored in Swift.

Pluggable Deployment and Monitoring
-----------------------------------

It was already mentioned in "General Workflow" that deployment mechanism will be pluggable allowing user to use
existing solutions to provision Hadoop cluster.

The same applies to monitoring. Instead of relying on its own monitoring module, EHO provides a capability to
plug in an existing solution like Nagios and Zabbix.

Both deployment and monitoring tools will be installed on stand-alone VMs, thus allowing a single instance to
manage/monitor several clusters at once.


Useful links
------------

.. toctree::
    :maxdepth: 4

    architecture
    restapi/v02
