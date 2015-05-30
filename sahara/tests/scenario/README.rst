System(scenario) tests for Sahara project
=========================================

How to run
----------

Create the yaml files for scenario tests ``etc/scenario/sahara-ci/simple-testcase.yaml``.
You can take a look at sample yaml files `How to write scenario files`_.

If you want to run scenario tests for one plugin, you should use the
yaml files with a scenario for this plugin:

.. sourcecode:: console

    $ tox -e scenario etc/scenario/sahara-ci/simple-testcase.yaml
..

For example, you want to run tests for the Vanilla plugin with the Hadoop
version 1.2.1. In this case you should use the following tox env:

.. sourcecode:: console

    $ tox -e scenario etc/scenario/sahara-ci/vanilla-1-2-1.yaml
..

If you want to run scenario tests for a few plugins or their versions, you
should use the several yaml files:

.. sourcecode:: console

    $ tox -e scenario etc/scenario/sahara-ci/vanilla-1-2-1.yaml etc/scenario/sahara-ci/vanilla-2-6-0.yaml ...
..

Here are a few more examples.

``tox -e scenario etc/scenario/sahara-ci/credential.yaml etc/scenario/sahara-ci/vanilla-2-6-0.yaml``
will run tests for Vanilla plugin with the Hadoop version 2.6.0 and credential
located in ``etc/scenario/sahara-ci/credential.yaml``.
For more information about writing scenario yaml files, see the section
section ``How to write scenario files``.

``tox -e scenario etc/scenario/sahara-ci`` will run tests from the test directory.

_`How to write scenario files`
==============================

You can write all sections in one or several files.

Field "concurrency"
-------------------

This field has integer value, and set concurrency for run tests

For example:
     ``concurrency: 2``

Section "credential"
--------------------

This section is dictionary-type.

+---------------------+--------+----------+------------------------------+-------------------------+
|   Fields            |  Type  | Required |          Default             |          Value          |
+=====================+========+==========+==============================+=========================+
| os_username         | string | True     | admin                        | user name for login     |
+---------------------+--------+----------+------------------------------+-------------------------+
| os_password         | string | True     | nova                         | password name for login |
+---------------------+--------+----------+------------------------------+-------------------------+
| os_tenant           | string | True     | admin                        | tenant name             |
+---------------------+--------+----------+------------------------------+-------------------------+
| os_auth_url         | string | True     | `http://localhost:5000/v2.0` | url for login           |
+---------------------+--------+----------+------------------------------+-------------------------+
| sahara_service_type | string |          | data-processing              | service type for sahara |
+---------------------+--------+----------+------------------------------+-------------------------+
| sahara_url          | string |          | None                         | url of sahara           |
+---------------------+--------+----------+------------------------------+-------------------------+


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

+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
|        Fields               |   Type  | Required |              Default              |                  Value                |
+=============================+=========+==========+===================================+=======================================+
| plugin_name                 | string  | True     |                                   | name of plugin                        |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| plugin_version              | string  | True     |                                   | version of plugin                     |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| image                       | string  | True     |                                   | name or id of image                   |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| node_group_templates        | object  |          |                                   | see `section "node_group_templates"`_ |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| cluster_template            | object  |          |                                   | see `section "cluster_template"`_     |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| cluster                     | object  |          |                                   | see `section "cluster"`_              |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| scaling                     | object  |          |                                   | see `section "scaling"`_              |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| timeout_check_transient     | integer |          | 300                               | timeout for checking transient        |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| timeout_poll_jobs_status    | integer |          | 1800                              | timeout for polling jobs state        |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| timeout_delete_resource     | integer |          | 300                               | timeout for delete resource           |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| timeout_poll_cluster_status | integer |          | 1800                              | timeout for polling cluster state     |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| scenario                    | array   |          | ['run_jobs', 'scale', 'run_jobs'] | array of checks                       |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| edp_jobs_flow               | string  |          |                                   | name of edp job flow                  |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+
| retain_resources            | boolean |          | False                             |                                       |
+-----------------------------+---------+----------+-----------------------------------+---------------------------------------+


Section "node_group_templates"
------------------------------

This section is an array-type.

+---------------------------+---------+----------+----------+---------------------------------------+
|           Fields          |   Type  | Required | Default  |                  Value                |
+===========================+=========+==========+==========+=======================================+
| name                      | string  | True     |          | name for node group template          |
+---------------------------+---------+----------+----------+---------------------------------------+
| flavor_id                 | string  | True     |          | id of flavor                          |
+---------------------------+---------+----------+----------+---------------------------------------+
| node_processes            | string  | True     |          | name of process                       |
+---------------------------+---------+----------+----------+---------------------------------------+
| description               | string  |          | Empty    | description for node group            |
+---------------------------+---------+----------+----------+---------------------------------------+
| volumes_per_node          | integer |          |    0     | minimum 0                             |
+---------------------------+---------+----------+----------+---------------------------------------+
| volumes_size              | integer |          |    0     | minimum 0                             |
+---------------------------+---------+----------+----------+---------------------------------------+
| auto_security_group       | boolean |          | True     |                                       |
+---------------------------+---------+----------+----------+---------------------------------------+
| security_group            | array   |          |          | security group                        |
+---------------------------+---------+----------+----------+---------------------------------------+
| node_configs              | object  |          |          | name_of_config_section: config: value |
+---------------------------+---------+----------+----------+---------------------------------------+
| availability_zone         | string  |          |          |                                       |
+---------------------------+---------+----------+----------+---------------------------------------+
| volumes_availability_zone | string  |          |          |                                       |
+---------------------------+---------+----------+----------+---------------------------------------+
| volume_type               | string  |          |          |                                       |
+---------------------------+---------+----------+----------+---------------------------------------+
| is_proxy_gateway          | boolean |          | False    |                                       |
+---------------------------+---------+----------+----------+---------------------------------------+


Section "cluster_template"
--------------------------

This section is dictionary-type.

+----------------------+---------+----------+-----------+---------------------------------------+
|        Fields        |  Type   | Required |  Default  |                 Value                 |
+======================+=========+==========+===========+=======================================+
| name                 | string  | True     |           | name for cluster template             |
+----------------------+---------+----------+-----------+---------------------------------------+
| description          | string  |          | Empty     | description                           |
+----------------------+---------+----------+-----------+---------------------------------------+
| cluster_configs      | object  |          |           | name_of_config_section: config: value |
+----------------------+---------+----------+-----------+---------------------------------------+
| node_group_templates | object  | True     |           | name_of_node_group: count             |
+----------------------+---------+----------+-----------+---------------------------------------+
| anti_affinity        | boolean |          | False     |                                       |
+----------------------+---------+----------+-----------+---------------------------------------+


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

This section has an object with a name from the `section "clusters"`_ field "edp_jobs_flow"
Object has sections of array-type.
Required: type

+-------------------+--------+----------+-----------+----------------------------------------------------------------------+
|       Fields      |  Type  | Required |  Default  |                                 Value                                |
+===================+========+==========+===========+======================================================================+
| type              | string | True     |           | "Pig", "Java", "MapReduce", "MapReduce.Streaming", "Hive", "Spark"   |
+-------------------+--------+----------+-----------+----------------------------------------------------------------------+
| input_datasource  | object |          |           | see `section "input_datasource"`_                                    |
+-------------------+--------+----------+-----------+----------------------------------------------------------------------+
| output_datasource | object |          |           | see `section "output_datasource"`_                                   |
+-------------------+--------+----------+-----------+----------------------------------------------------------------------+
| main_lib          | object |          |           | see `section "main_lib"`_                                            |
+-------------------+--------+----------+-----------+----------------------------------------------------------------------+
| additional_libs   | object |          |           | see `section "additional_libs"`_                                     |
+-------------------+--------+----------+-----------+----------------------------------------------------------------------+
| configs           | dict   |          | Empty     | config: value                                                        |
+-------------------+--------+----------+-----------+----------------------------------------------------------------------+
| args              | array  |          | Empty     | array of args                                                        |
+-------------------+--------+----------+-----------+----------------------------------------------------------------------+


Section "input_datasource"
--------------------------

Required: type, source
This section is dictionary-type.

+--------+--------+----------+-----------+---------------------------+
| Fields |  Type  | Required |  Default  |            Value          |
+========+========+==========+===========+===========================+
| type   | string | True     |           | "swift", "hdfs", "maprfs" |
+--------+--------+----------+-----------+---------------------------+
| source | string | True     |           | uri of source             |
+--------+--------+----------+-----------+---------------------------+


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
