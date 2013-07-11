Savanna Features
================

Validation Mechanism
--------------------

Savanna runs a number of checks before performing any operation.
This checks are designed to prevent user form creating incorrectly configured templates or deploying invalid cluster topologies.

Savanna REST API will return 400 status code with a description message if any of checks fails.

Configuration validations
~~~~~~~~~~~~~~~~~~~~~~~~~

When a configuration entry is registered by a provisioning plugin, it ma be marked as optional.
If not so and there is no default value for this configuration,
user should provide one.

Also any configuration entry has a type parameter, which means for example,
that user cannot set a random string value where an integer is expected.

Cluster Topology validations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When user starts a Hadoop Cluster using a reference plugin implementation (Vanilla plugin),
the cluster topology user has built is verified for consistency.

Before launching any VMs Vanilla plugin will check that the set of Node Groups user has defined for a Cluster can actually work.

One of such checks is :

If there is no Node Group running a NameNode process, but there are DataNodes, HDFS service will not start, so user will get a validation error.

One more scenario is:

If a Node Group has any of master processes (NameNode or JobTracker) in it
and user is going to launch more than one instance in this Node Group, that will also result in a validation error.

Cluster Scaling
---------------

The mechanism of scaling an existing Cluster is designed to enable user to change the number of running instances without creating a new Cluster.

User may change number of instances in existing Node groups or even add any Node Groups if topology should be changed.

Changes made with Cluster scaling requests are also validated as well as requests to create a Cluster.

Scaling is supported in Vanilla plugin.

