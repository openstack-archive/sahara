Plugin SPI
==========

Plugin interface
----------------

get_versions()
~~~~~~~~~~~~~~

Returns all available versions of the plugin. Depending on the plugin, this
version may map directly to the HDFS version, or it may not; check your
plugin's documentation. It is responsibility of the plugin to make sure that
all required images for each hadoop version are available, as well as configs
and whatever else that plugin needs to create the Hadoop cluster.

*Returns*: list of strings representing plugin versions

*Example return value*: ["1.2.1", "2.3.0", "2.4.1"]

get_configs( hadoop_version )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lists all configs supported by the plugin with descriptions, defaults, and
targets for which this config is applicable.

*Returns*: list of configs

*Example return value*: (("JobTracker heap size", "JobTracker heap size, in
MB", "int", "512", `"mapreduce"`, "node", True, 1))

get_node_processes( hadoop_version )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns all supported services and node processes for a given Hadoop version.
Each node process belongs to a single service and that relationship is
reflected in the returned dict object.  See example for details.

*Returns*: dictionary having entries (service -> list of processes)

*Example return value*: {"mapreduce": ["tasktracker", "jobtracker"], "hdfs":
["datanode", "namenode"]}

get_required_image_tags( hadoop_version )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lists tags that should be added to OpenStack Image via Image Registry. Tags
are used to filter Images by plugin and hadoop version.

*Returns*: list of tags

*Example return value*: ["tag1", "some_other_tag", ...]

validate( cluster )
~~~~~~~~~~~~~~~~~~~

Validates a given cluster object. Raises a *SaharaException* with a meaningful
message in the case of validation failure.

*Returns*: None

*Example exception*: <NotSingleNameNodeException {code='NOT_SINGLE_NAME_NODE',
message='Hadoop cluster should contain only 1 NameNode instance. Actual NN
count is 2' }>

validate_scaling( cluster, existing, additional )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To be improved.

Validates a given cluster before scaling operation.

*Returns*: list of validation_errors

update_infra( cluster )
~~~~~~~~~~~~~~~~~~~~~~~

This method is no longer used now that Sahara utilizes Heat for OpenStack
resource provisioning, and is not currently utilized by any plugin.

*Returns*: None

configure_cluster( cluster )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configures cluster on the VMs provisioned by sahara. In this function the
plugin should perform all actions like adjusting OS, installing required
packages (including Hadoop, if needed), configuring Hadoop, etc.

*Returns*: None

start_cluster( cluster )
~~~~~~~~~~~~~~~~~~~~~~~~

Start already configured cluster. This method is guaranteed to be called only
on a cluster which was already prepared with configure_cluster(...) call.

*Returns*: None

scale_cluster( cluster, instances )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scale an existing cluster with additional instances. The instances argument is
a list of ready-to-configure instances. Plugin should do all configuration
operations in this method and start all services on those instances.

*Returns*: None

.. _get_edp_engine:

get_edp_engine( cluster, job_type )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns an EDP job engine object that supports the specified job_type on the
given cluster, or None if there is no support. The EDP job engine object
returned must implement the interface described in :doc:`edp-spi`.  The
job_type is a String matching one of the job types listed in
:ref:`edp_spi_job_types`.

*Returns*: an EDP job engine object or None

decommission_nodes( cluster, instances )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scale cluster down by removing a list of instances. The plugin should stop
services on the provided list of instances. The plugin also may need to update
some configurations on other instances when nodes are removed; if so, this
method must perform that reconfiguration.

*Returns*: None

on_terminate_cluster( cluster )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When user terminates cluster, sahara simply shuts down all the cluster VMs.
This method is guaranteed to be invoked before that, allowing the plugin to do
some clean-up.

*Returns*: None

get_open_ports( node_group )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When user requests sahara to automatically create a security group for the
node group (``auto_security_group`` property set to True), sahara will call
this plugin method to get a list of ports that need to be opened.

*Returns*: list of ports to be open in auto security group for the given node
group

get_edp_job_types( versions )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optional method, which provides the ability to see all supported job types for
specified plugin versions.

*Returns*: dict with supported job types for specified versions of plugin

recommend_configs( self, cluster, scaling=False )
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optional method, which provides recommendations for cluster configuration
before creating/scaling operation.

get_image_arguments( self, hadoop_version ):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optional method, which gets the argument set taken by the plugin's image
generator, or NotImplemented if the plugin does not provide image generation
support. See :doc:`../contributor/image-gen`.

*Returns*: A sequence with items of type sahara.plugins.images.ImageArgument.

pack_image( self, hadoop_version, remote, test_only=False, ... ):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Optional method which packs an image for registration in Glance and use by
Sahara. This method is called from the image generation CLI rather than from
the Sahara api or engine service. See :doc:`../contributor/image-gen`.

*Returns*: None (modifies the image pointed to by the remote in-place.)

validate_images( self, cluster, test_only=False, image_arguments=None ):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Validates the image to be used to create a cluster, to ensure that it meets
the specifications of the plugin. See :doc:`../contributor/image-gen`.

*Returns*: None; may raise a sahara.plugins.exceptions.ImageValidationError


Object Model
============

Here is a description of all the objects involved in the API.

Notes:

  - clusters and node_groups have 'extra' fields allowing the plugin to
    persist any supplementary info about the cluster.
  - node_process is just a process that runs on some node in cluster.

Example list of node processes:

1. jobtracker
2. namenode
3. tasktracker
4. datanode

- Each plugin may have different names for the same processes.

Config
------

An object, describing one configuration entry

+-------------------+--------+------------------------------------------------+
| Property          | Type   | Description                                    |
+===================+========+================================================+
| name              | string | Config name.                                   |
+-------------------+--------+------------------------------------------------+
| description       | string | A hint for user, what this config is used for. |
+-------------------+--------+------------------------------------------------+
| config_type       | enum   | possible values are: 'string', 'integer',      |
|                   |        | 'boolean', 'enum'.                             |
+-------------------+--------+------------------------------------------------+
| config_values     | list   | List of possible values, if config_type is     |
|                   |        | enum.                                          |
+-------------------+--------+------------------------------------------------+
| default_value     | string | Default value for config.                      |
+-------------------+--------+------------------------------------------------+
| applicable_target | string | The target could be either a service returned  |
|                   |        | by get_node_processes(...) call                |
|                   |        | in form of 'service:<service name>', or        |
|                   |        | 'general'.                                     |
+-------------------+--------+------------------------------------------------+
| scope             | enum   | Could be either 'node' or 'cluster'.           |
+-------------------+--------+------------------------------------------------+
| is_optional       | bool   | If is_optional is False and no default_value   |
|                   |        | is specified, user must provide a value.       |
+-------------------+--------+------------------------------------------------+
| priority          | int    | 1 or 2. A Hint for UI. Configs with priority   |
|                   |        | *1* are always displayed.                      |
|                   |        | Priority *2* means user should click a button  |
|                   |        | to see the config.                             |
+-------------------+--------+------------------------------------------------+


User Input
----------

Value provided by user for a specific config.

+----------+--------+--------------------------------------------------------+
| Property | Type   | Description                                            |
+==========+========+========================================================+
| config   | config | A config object for which this user_input is provided. |
+----------+--------+--------------------------------------------------------+
| value    | ...    | Value for the config. Type depends on Config type.     |
+----------+--------+--------------------------------------------------------+


Instance
--------

An instance created for cluster.

+---------------+---------+---------------------------------------------------+
| Property      | Type    | Description                                       |
+===============+=========+===================================================+
| instance_id   | string  | Unique instance identifier.                       |
+---------------+---------+---------------------------------------------------+
| instance_name | string  | OpenStack instance name.                          |
+---------------+---------+---------------------------------------------------+
| internal_ip   | string  | IP to communicate with other instances.           |
+---------------+---------+---------------------------------------------------+
| management_ip | string  | IP of instance, accessible outside of internal    |
|               |         | network.                                          |
+---------------+---------+---------------------------------------------------+
| volumes       | list    | List of volumes attached to instance. Empty if    |
|               |         | ephemeral drive is used.                          |
+---------------+---------+---------------------------------------------------+
| nova_info     | object  | Nova instance object.                             |
+---------------+---------+---------------------------------------------------+
| username      | string  | Username, that sahara uses for establishing       |
|               |         | remote connections to instance.                   |
+---------------+---------+---------------------------------------------------+
| hostname      | string  | Same as instance_name.                            |
+---------------+---------+---------------------------------------------------+
| fqdn          | string  | Fully qualified domain name for this instance.    |
+---------------+---------+---------------------------------------------------+
| remote        | helpers | Object with helpers for performing remote         |
|               |         | operations.                                       |
+---------------+---------+---------------------------------------------------+


Node Group
----------

Group of instances.

+----------------------+--------+---------------------------------------------+
| Property             | Type   | Description                                 |
+======================+========+=============================================+
| name                 | string | Name of this Node Group in Cluster.         |
+----------------------+--------+---------------------------------------------+
| flavor_id            | string | OpenStack Flavor used to boot instances.    |
+----------------------+--------+---------------------------------------------+
| image_id             | string | Image id used to boot instances.            |
+----------------------+--------+---------------------------------------------+
| node_processes       | list   | List of processes running on each instance. |
+----------------------+--------+---------------------------------------------+
| node_configs         | dict   | Configs dictionary, applied to instances.   |
+----------------------+--------+---------------------------------------------+
| volumes_per_node     | int    | Number of volumes mounted to each instance. |
|                      |        | 0 means use ephemeral drive.                |
+----------------------+--------+---------------------------------------------+
| volumes_size         | int    | Size of each volume (GB).                   |
+----------------------+--------+---------------------------------------------+
| volumes_mount_prefix | string | Prefix added to mount path of each volume.  |
+----------------------+--------+---------------------------------------------+
| floating_ip_pool     | string | Floating IP Pool name. All instances in the |
|                      |        | Node Group will have Floating IPs assigned  |
|                      |        | from this pool.                             |
+----------------------+--------+---------------------------------------------+
| count                | int    | Number of instances in this Node Group.     |
+----------------------+--------+---------------------------------------------+
| username             | string | Username used by sahara to establish remote |
|                      |        | connections to instances.                   |
+----------------------+--------+---------------------------------------------+
| configuration        | dict   | Merged dictionary of node configurations    |
|                      |        | and cluster configurations.                 |
+----------------------+--------+---------------------------------------------+
| storage_paths        | list   | List of directories where storage should be |
|                      |        | placed.                                     |
+----------------------+--------+---------------------------------------------+

Cluster
-------

Contains all relevant info about cluster.  This object is provided to the
plugin for both cluster creation and scaling.  The "Cluster Lifecycle" section
below further specifies which fields are filled at which moment.

+----------------------------+--------+---------------------------------------+
| Property                   | Type   | Description                           |
+============================+========+=======================================+
| name                       | string | Cluster name.                         |
+----------------------------+--------+---------------------------------------+
| project_id                 | string | OpenStack Project id where this       |
|                            |        | Cluster is available.                 |
+----------------------------+--------+---------------------------------------+
| plugin_name                | string | Plugin name.                          |
+----------------------------+--------+---------------------------------------+
| hadoop_version             | string | Hadoop version running on instances.  |
+----------------------------+--------+---------------------------------------+
| default_image_id           | string | OpenStack image used to boot          |
|                            |        | instances.                            |
+----------------------------+--------+---------------------------------------+
| node_groups                | list   | List of Node Groups.                  |
+----------------------------+--------+---------------------------------------+
| cluster_configs            | dict   | Dictionary of Cluster scoped          |
|                            |        | configurations.                       |
+----------------------------+--------+---------------------------------------+
| cluster_template_id        | string | Cluster Template used for Node Groups |
|                            |        | and Configurations.                   |
+----------------------------+--------+---------------------------------------+
| user_keypair_id            | string | OpenStack keypair added to instances  |
|                            |        | to make them accessible for user.     |
+----------------------------+--------+---------------------------------------+
| neutron_management_network | string | Neutron network ID. Instances will    |
|                            |        | get fixed IPs in this network.        |
+----------------------------+--------+---------------------------------------+
| anti_affinity              | list   | List of processes that will be run on |
|                            |        | different hosts.                      |
+----------------------------+--------+---------------------------------------+
| description                | string | Cluster Description.                  |
+----------------------------+--------+---------------------------------------+
| info                       | dict   | Dictionary for additional information.|
+----------------------------+--------+---------------------------------------+


Validation Error
----------------

Describes what is wrong with one of the values provided by user.

+---------------+--------+-----------------------------------------------+
| Property      | Type   | Description                                   |
+===============+========+===============================================+
| config        | config | A config object that is not valid.            |
+---------------+--------+-----------------------------------------------+
| error_message | string | Message that describes what exactly is wrong. |
+---------------+--------+-----------------------------------------------+
