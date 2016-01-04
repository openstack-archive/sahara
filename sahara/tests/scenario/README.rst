System(scenario) tests for Sahara project
=========================================

How to run
----------

Create the YAML and/or the YAML mako template files for scenario tests
``etc/scenario/sahara-ci/simple-testcase.yaml``.
You can take a look at sample YAML files `How to write scenario files`_.

If you want to run scenario tests for one plugin, you should use the
YAML files with a scenario for the specific plugin:

.. sourcecode:: console

    $ tox -e scenario etc/scenario/sahara-ci/simple-testcase.yaml
..

or, if the file is a YAML Mako template:

.. sourcecode:: console

    $ tox -e scenario -- -V templatevars.ini etc/scenario/sahara-ci/vanilla-2.7.1.yaml.mako
..

where templatevars.ini contains the values of the variables referenced
by ``vanilla-2.7.1.yaml.mako``.

For example, you want to run tests for the Vanilla plugin with the Hadoop
version 2.7.1 In this case you should create ``templatevars.ini`` with
the appropriate values (see the section `Variables and sahara-ci templates`_)
and use the following tox env:

.. sourcecode:: console

    $ tox -e scenario -- -V templatevars.ini etc/scenario/sahara-ci/vanilla-2.7.1.yaml.mako
..

If you want to run scenario tests for a few plugins or their versions, you
should use the several YAML and/or YAML Mako template files:

.. sourcecode:: console

    $ tox -e scenario -- -V templatevars.ini etc/scenario/sahara-ci/cdh-5.4.0.yaml.mako etc/scenario/sahara-ci/vanilla-2.7.1.yaml.mako ...
..

Here are a few more examples.

.. sourcecode:: console

    $ tox -e scenario -- -V templatevars.ini etc/scenario/sahara-ci/credentials.yaml.mako etc/scenario/sahara-ci/vanilla-2.7.1.yaml.mako

..

will run tests for Vanilla plugin with the Hadoop version 2.7.1 and credential
located in ``etc/scenario/sahara-ci/credentials.yaml.mako``, replacing the variables
included into ``vanilla-2.7.1.yaml.mako`` with the values defined into
``templatevars.ini``.
For more information about writing scenario YAML files, see the section
section `How to write scenario files`_.

``tox -e scenario etc/scenario/sahara-ci`` will run tests from the test directory.

Also, you can validate your yaml-files using flag ``--validate`` via command:

.. sourcecode:: console

    $ tox -e scenario -- --validate -V templatevars.ini etc/scenario/sahara-ci/credantials.yaml.mako etc/scenario/sahara-ci/vanilla-2.7.1.yaml.mako

..

Template variables
------------------
The variables used in the Mako template files are replaced with the values from a
config file, whose name is passed to the test runner through the ``-V`` parameter.

The format of the config file is an INI-style file, as accepted by the Python
ConfigParser module. The key/values must be specified in the DEFAULT section.

Example of template variables file:
.. sourcecode:: ini

    [DEFAULT]
    OS_USERNAME: demo
    OS_TENANT_NAME: demo
    OS_PASSWORD: foobar
    ...
    network_type: neutron
    ...

..

Variables and sahara-ci templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The following variables are currently used by sahara-ci templates:

+-----------------------------+--------+--------------------------------------------------------------+
|   Variable                  |  Type  |          Value                                               |
+=============================+========+==============================================================+
| OS_USERNAME                 | string | user name for login                                          |
+-----------------------------+--------+--------------------------------------------------------------+
| OS_PASSWORD                 | string | password for login                                           |
+-----------------------------+--------+--------------------------------------------------------------+
| OS_TENANT_NAME              | string | tenant name                                                  |
+-----------------------------+--------+--------------------------------------------------------------+
| OS_AUTH_URL                 | string | url for authentication                                       |
+-----------------------------+--------+--------------------------------------------------------------+
| network_type                | string | neutron or nova-network                                      |
+-----------------------------+--------+--------------------------------------------------------------+
| network_private_name        | string | private network name for OS_TENANT_NAME                      |
+-----------------------------+--------+--------------------------------------------------------------+
| network_public_name         | string | public network name                                          |
+-----------------------------+--------+--------------------------------------------------------------+
| <plugin_name_version>_name  | string | name of the image to be used for the specific plugin/version |
+-----------------------------+--------+--------------------------------------------------------------+
| {ci,medium,large}_flavor_id | string | IDs of flavor with different size                            |
+-----------------------------+--------+--------------------------------------------------------------+


_`How to write scenario files`
==============================

You can write all sections in one or several files, which can be simple YAML files
or YAML-based Mako templates (.yaml.mako or yml.mako).

Field "concurrency"
-------------------

This field has integer value, and set concurrency for run tests

For example:
     ``concurrency: 2``

Section "credentials"
--------------------

This section is dictionary-type.

+---------------------+--------+----------+------------------------------+---------------------------------+
|   Fields            |  Type  | Required |          Default             |               Value             |
+=====================+========+==========+==============================+=================================+
| os_username         | string | True     | admin                        | user name for login             |
+---------------------+--------+----------+------------------------------+---------------------------------+
| os_password         | string | True     | nova                         | password for login              |
+---------------------+--------+----------+------------------------------+---------------------------------+
| os_tenant           | string | True     | admin                        | tenant name                     |
+---------------------+--------+----------+------------------------------+---------------------------------+
| os_auth_url         | string | True     | `http://localhost:5000/v2.0` | url for login                   |
+---------------------+--------+----------+------------------------------+---------------------------------+
| sahara_service_type | string |          | data-processing              | service type for sahara         |
+---------------------+--------+----------+------------------------------+---------------------------------+
| sahara_url          | string |          | None                         | url of sahara                   |
+---------------------+--------+----------+------------------------------+---------------------------------+
| ssl_cert            | string |          | None                         | ssl certificate for all clients |
+---------------------+--------+----------+------------------------------+---------------------------------+
| ssl_verify          | boolean|          | True                         | enable verify ssl for sahara    |
+---------------------+--------+----------+------------------------------+---------------------------------+

Section "network"
-----------------

This section is dictionary-type.

+-----------------------------+---------+----------+----------+-------------------------------+
|           Fields            |   Type  | Required | Default  |            Value              |
+=============================+=========+==========+==========+===============================+
| private_network             | string  |  True    | private  | name or id of private network |
+-----------------------------+---------+----------+----------+-------------------------------+
| public_network              | string  |  True    | public   | name or id of private network |
+-----------------------------+---------+----------+----------+-------------------------------+
| type                        | string  |          | neutron  | "neutron" or "nova-network"   |
+-----------------------------+---------+----------+----------+-------------------------------+
| auto_assignment_floating_ip | boolean |          | False    |                               |
+-----------------------------+---------+----------+----------+-------------------------------+


Section "clusters"
------------------

This sections is an array-type.

+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
|        Fields               |   Type  | Required |              Default              |                       Value                    |
+=============================+=========+==========+===================================+================================================+
| plugin_name                 | string  | True     |                                   | name of plugin                                 |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| plugin_version              | string  | True     |                                   | version of plugin                              |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| image                       | string  | True     |                                   | name or id of image                            |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| existing_cluster            | string  |          |                                   | cluster name or id for testing                 |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| key_name                    | string  |          |                                   | name of registered ssh key for testing cluster |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| node_group_templates        | object  |          |                                   | see `section "node_group_templates"`_          |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| cluster_template            | object  |          |                                   | see `section "cluster_template"`_              |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| cluster                     | object  |          |                                   | see `section "cluster"`_                       |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| scaling                     | object  |          |                                   | see `section "scaling"`_                       |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| timeout_check_transient     | integer |          | 300                               | timeout for checking transient                 |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| timeout_poll_jobs_status    | integer |          | 1800                              | timeout for polling jobs state                 |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| timeout_delete_resource     | integer |          | 300                               | timeout for delete resource                    |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| timeout_poll_cluster_status | integer |          | 1800                              | timeout for polling cluster state              |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| scenario                    | array   |          | ['run_jobs', 'scale', 'run_jobs'] | array of checks                                |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| edp_jobs_flow               | string  |          |                                   | name of edp job flow                           |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+
| retain_resources            | boolean |          | False                             |                                                |
+-----------------------------+---------+----------+-----------------------------------+------------------------------------------------+


Section "node_group_templates"
------------------------------

This section is an array-type.

+---------------------------+------------------+----------+------------+--------------------------------------------------+
|           Fields          |       Type       | Required |   Default  |                      Value                       |
+===========================+==================+==========+============+==================================================+
| name                      | string           | True     |            | name for node group template                     |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| flavor                    | string or object | True     |            | name or id of flavor, or see `section "flavor"`_ |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| node_processes            | string           | True     |            | name of process                                  |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| description               | string           |          | Empty      | description for node group                       |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| volumes_per_node          | integer          |          |     0      | minimum 0                                        |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| volumes_size              | integer          |          |     0      | minimum 0                                        |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| auto_security_group       | boolean          |          | True       |                                                  |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| security_group            | array            |          |            | security group                                   |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| node_configs              | object           |          |            | name_of_config_section: config: value            |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| availability_zone         | string           |          |            |                                                  |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| volumes_availability_zone | string           |          |            |                                                  |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| volume_type               | string           |          |            |                                                  |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| is_proxy_gateway          | boolean          |          | False      | use this node as proxy gateway                   |
+---------------------------+------------------+----------+------------+--------------------------------------------------+
| edp_batching              | integer          |          | count jobs | use for batching jobs                            |
+---------------------------+------------------+----------+------------+--------------------------------------------------+

Section "flavor"
----------------

This section is an dictionary-type.

+----------------+---------+----------+---------------+--------------------------------+
|     Fields     |  Type   | Required |    Default    |              Value             |
+================+=========+==========+===============+================================+
| name           | string  |          | auto-generate | name for flavor                |
+----------------+---------+----------+---------------+--------------------------------+
| id             | string  |          | auto-generate | id for flavor                  |
+----------------+---------+----------+---------------+--------------------------------+
| vcpus          | integer |          |       1       | number of VCPUs for the flavor |
+----------------+---------+----------+---------------+--------------------------------+
| ram            | integer |          |       1       | memory in MB for the flavor    |
+----------------+---------+----------+---------------+--------------------------------+
| root_disk      | integer |          |       0       | size of local disk in GB       |
+----------------+---------+----------+---------------+--------------------------------+
| ephemeral_disk | integer |          |       0       | ephemeral space in MB          |
+----------------+---------+----------+---------------+--------------------------------+
| swap_disk      | integer |          |       0       | swap space in MB               |
+----------------+---------+----------+---------------+--------------------------------+


Section "cluster_template"
--------------------------

This section is dictionary-type.

+----------------------+--------+----------+-----------+---------------------------------------+
|        Fields        |  Type  | Required |  Default  |                 Value                 |
+======================+========+==========+===========+=======================================+
| name                 | string | True     |           | name for cluster template             |
+----------------------+--------+----------+-----------+---------------------------------------+
| description          | string |          | Empty     | description                           |
+----------------------+--------+----------+-----------+---------------------------------------+
| cluster_configs      | object |          |           | name_of_config_section: config: value |
+----------------------+--------+----------+-----------+---------------------------------------+
| node_group_templates | object | True     |           | name_of_node_group: count             |
+----------------------+--------+----------+-----------+---------------------------------------+
| anti_affinity        | array  |          | Empty     | array of roles                        |
+----------------------+--------+----------+-----------+---------------------------------------+


Section "cluster"
-----------------

This section is dictionary-type.

+--------------+---------+----------+---------+------------------+
|    Fields    |  Type   | Required | Default |       Value      |
+==============+=========+==========+=========+==================+
| name         | string  | True     | Empty   | name for cluster |
+--------------+---------+----------+---------+------------------+
| description  | string  |          | Empty   | description      |
+--------------+---------+----------+---------+------------------+
| is_transient | boolean |          | False   | value            |
+--------------+---------+----------+---------+------------------+


Section "scaling"
-----------------

This section is an array-type.

+------------+---------+----------+-----------+--------------------+
|   Fields   |  Type   | Required |  Default  |       Value        |
+============+=========+==========+===========+====================+
| operation  | string  | True     |           | "add" or "resize"  |
+------------+---------+----------+-----------+--------------------+
| node_group | string  | True     | Empty     | name of node group |
+------------+---------+----------+-----------+--------------------+
| size       | integer | True     | Empty     | count node group   |
+------------+---------+----------+-----------+--------------------+


Section "edp_jobs_flow"
-----------------------

This section has an object with a name from the `section "clusters"`_ field "edp_jobs_flows"
Object has sections of array-type.
Required: type

+-------------------+--------+----------+-----------+-----------------------------------------------------------------------------+
|       Fields      |  Type  | Required |  Default  |                                 Value                                       |
+===================+========+==========+===========+=============================================================================+
| type              | string | True     |           | "Pig", "Java", "MapReduce", "MapReduce.Streaming", "Hive", "Spark", "Shell" |
+-------------------+--------+----------+-----------+-----------------------------------------------------------------------------+
| input_datasource  | object |          |           | see `section "input_datasource"`_                                           |
+-------------------+--------+----------+-----------+-----------------------------------------------------------------------------+
| output_datasource | object |          |           | see `section "output_datasource"`_                                          |
+-------------------+--------+----------+-----------+-----------------------------------------------------------------------------+
| main_lib          | object |          |           | see `section "main_lib"`_                                                   |
+-------------------+--------+----------+-----------+-----------------------------------------------------------------------------+
| additional_libs   | object |          |           | see `section "additional_libs"`_                                            |
+-------------------+--------+----------+-----------+-----------------------------------------------------------------------------+
| configs           | dict   |          | Empty     | config: value                                                               |
+-------------------+--------+----------+-----------+-----------------------------------------------------------------------------+
| args              | array  |          | Empty     | array of args                                                               |
+-------------------+--------+----------+-----------+-----------------------------------------------------------------------------+


Section "input_datasource"
--------------------------

Required: type, source
This section is dictionary-type.

+---------------+--------+----------+-----------+---------------------------+
|    Fields     |  Type  | Required |  Default  |            Value          |
+===============+========+==========+===========+===========================+
| type          | string | True     |           | "swift", "hdfs", "maprfs" |
+---------------+--------+----------+-----------+---------------------------+
| hdfs_username | string |          |           | username for hdfs         |
+---------------+--------+----------+-----------+---------------------------+
| source        | string | True     |           | uri of source             |
+---------------+--------+----------+-----------+---------------------------+


Section "output_datasource"
---------------------------

Required: type, destination
This section is dictionary-type.

+-------------+--------+----------+-----------+---------------------------+
| Fields      |  Type  | Required |  Default  |           Value           |
+=============+========+==========+===========+===========================+
| type        | string | True     |           | "swift", "hdfs", "maprfs" |
+-------------+--------+----------+-----------+---------------------------+
| destination | string | True     |           | uri of source             |
+-------------+--------+----------+-----------+---------------------------+


Section "main_lib"
------------------

Required: type, source
This section is dictionary-type.

+--------+--------+----------+-----------+----------------------+
| Fields |  Type  | Required |  Default  |         Value        |
+========+========+==========+===========+======================+
| type   | string | True     |           | "swift or "database" |
+--------+--------+----------+-----------+----------------------+
| source | string | True     |           | uri of source        |
+--------+--------+----------+-----------+----------------------+


Section "additional_libs"
-------------------------

Required: type, source
This section is an array-type.

+--------+--------+----------+-----------+----------------------+
| Fields |  Type  | Required |  Default  |         Value        |
+========+========+==========+===========+======================+
| type   | string | True     |           | "swift or "database" |
+--------+--------+----------+-----------+----------------------+
| source | string | True     |           | uri of source        |
+--------+--------+----------+-----------+----------------------+
