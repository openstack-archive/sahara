Sahara Default Template CLI
===========================

The *sahara-templates* application is a simple CLI for managing default
templates in Sahara. This document gives an overview of default templates
and explains how to use the CLI.

Default Templates Overview
--------------------------

The goal of the default template facility in Sahara is to make cluster
launching quick and easy by providing users with a stable set of pre-generated
node group and cluster templates for each of the Sahara provisioning plugins.

Template sets are defined in .json files grouped into directories. The CLI
reads these template sets and writes directly to the Sahara database.

Default templates may only be created, modified, or deleted via the CLI --
operations through the python-saharaclient or REST API are restricted.

JSON Files
----------

Cluster and node group templates are defined in .json files.

A very simple cluster template JSON file might look like this:

.. code:: python

  {
      "plugin_name": "vanilla",
      "hadoop_version": "2.7.1",
      "node_groups": [
          {
              "name": "master",
              "count": 1,
              "node_group_template_id": "{master}"
          },
          {
              "name": "worker",
              "count": 3,
              "node_group_template_id": "{worker}"
          }
      ],
      "name": "cluster-template"
  }

The values of the *node_group_template_id* fields are the
names of node group templates in set braces. In this example,
*master* and *worker* are the names of node group templates defined in
.json files in the same directory. When the CLI processes the
directory, it will create the node group templates first and
then substitute the appropriate id values for the name references
when it creates the cluster template.

Configuration Files and Value Substitutions
-------------------------------------------

The CLI supports value substitution for a limited set of fields.
For cluster templates, the following fields may use substitution:

* default_image_id
* neutron_management_network

For node group templates, the following fields may use substitution:

* image_id
* flavor_id
* floating_ip_pool

Substitution is indicated for one of these fields in a .json file
when the value is the name of the field in set braces. Here is an example
of a node group template file that uses substitution for *flavor_id*:

.. code:: python

  {
      "plugin_name": "vanilla",
      "hadoop_version": "2.7.1",
      "node_processes": [
          "namenode",
          "resourcemanager",
          "oozie",
          "historyserver"
      ],
      "name": "master",
      "flavor_id": "{flavor_id}",
      "floating_ip_pool": "{floating_ip_pool}"
  }

The values for *flavor_id* and *floating_ip_pool* in this template
will come from a configuration file.

If a configuration value is found for the substitution, the value will
be replaced. If a configuration value is not found, the field will be
omitted from the template. (In this example, *flavor_id* is a required
field of node group templates and the template will fail validation
if there is no substitution value specified. However, *floating_ip_pool*
is not required and so the template will still pass validation if it
is omitted).

The CLI will look for configuration sections with names based on
the *plugin_name*, *hadoop_version*, and *name* fields in the
template. It will look for sections in the following order:

* **[<name>]**

  May contain fields only for the type of the named template

  If templates are named in an **unambiguous** way, the template
  name alone can be a used as the name of the config section.
  This produces shorter names and aids readability when there
  is a one-to-one mapping between template names and config
  sections.

* **[<plugin_name>_<hadoop_version>_<name>]**

  May contain fields only for the type of the named template

  This form unambiguously applies to a specific template for
  a specific plugin.

* **[<plugin_name>_<hadoop_version>]**

  May contain node group or cluster template fields

* **[<plugin_name>]**

  May contain node group or cluster template fields

* **[DEFAULT]**

  May contain node group or cluster template fields

If we have the following configuration file in our example
the CLI will find the value of *flavor_id* for the *master* template
in the first configuration section and the value for *floating_ip_pool*
in the third section:

.. code:: python

  [vanilla_2.7.1_master]
  # This is named for the plugin, version, and template.
  # It may contain only node group template fields.
  flavor_id = 5
  image_id = b7883f8a-9a7f-42cc-89a2-d3c8b1cc7b28

  [vanilla_2.7.1]
  # This is named for the plugin and version.
  # It may contain fields for both node group and cluster templates.
  flavor_id = 4
  neutron_management_network = 9973da0b-68eb-497d-bd48-d85aca37f088

  [vanilla]
  # This is named for the plugin.
  # It may contain fields for both node group and cluster templates.
  flavor_id = 3
  default_image_id = 89de8d21-9743-4d20-873e-7677973416dd
  floating_ip_pool = my_pool

  [DEFAULT]
  # This is the normal default section.
  # It may contain fields for both node group and cluster templates.
  flavor_id = 2

Sample Configuration File
-------------------------

A sample configuration file is provided in
*sahara/plugins/default_templates/template.conf*. This
file sets the *flavor_id* for most of the node group templates
supplied with Sahara to 2 which indicates the *m1.small*
flavor in a default OpenStack deployment.

The master node templates for the CDH plugin have the
*flavor_id* set to 4 which indicates the *m1.large* flavor,
since these nodes require more resources.

This configuration file may be used with the CLI as is, or
it may be copied and modified. Note that multiple configuration
files may be passed to the CLI by repeating the *--config-file*
option.

Other Special Configuration Parameters
--------------------------------------

The only configuration parameter that is strictly required is
the *connection* parameter in the *database* section. Without this
value the CLI will not be able to connect to the Sahara database.

By default, the CLI will use the value of the *plugins* parameter
in the [DEFAULT] section on *update* to filter the templates that
will be created or updated. This parameter in Sahara defaults to
the set of fully supported plugins. To restrict the set of plugins
for the *update* operation set this parameter or use the
*--plugin-name* option.

Directory Structure
-------------------

The structure of the directory holding .json files for the CLI is
very flexible.  The CLI will begin processing at the designated
starting directory and recurse through subdirectories.

At each directory level, the CLI will look for .json files to
define a set of default templates. Cluster templates may reference
node group templates in the same set by name. Templates at different
levels in the directory structure are not in the same set.

Plugin name and version are determined from the values in the .json
files, not by the file names or the directory structure.

Recursion may be turned off with the "-n" option (see below).

The default starting directory is *sahara/plugins/default_templates*

Example CLI Commands
--------------------

For ``update``, ``delete``, ``node-group-template-delete``, and
``cluster-template-delete`` operations, the tenant must always be specified.
For ``node-group-template-delete-id`` and ``cluster-template-delete-id``
tenant is not required.
All useful information about activity by the CLI is logged

Create/update all of the default templates bundled with Sahara. Use the standard
Sahara configuration file in */etc/sahara/sahara.conf* to specify the plugin list
and the database connection string and another configuration file to supply
the *flavor_id* values::

  $ sahara-templates --config-file /etc/sahara/sahara.conf --config-file myconfig update -t $TENANT_ID

Create/update default templates from the directory *mypath*::

  $ sahara-templates --config-file myconfig update -t $TENANT_ID -d mypath

Create/update default templates from the directory *mypath* but do not descend
into subdirectories::

  $ sahara-templates --config-file myconfig update -t $TENANT_ID -d mypath -n

Create/update default templates bundled with Sahara for just the vanilla plugin::

  $ sahara-templates --config-file myconfig update -t $TENANT_ID -p vanilla

Create/update default templates bundled with Sahara for just version 2.7.1
of the vanilla plugin::

  $ sahara-templates --config-file myconfig update -t $TENANT_ID -p vanilla -pv 2.7.1

Create/update default templates bundled with Sahara for just version 2.7.1
of the vanilla plugin and version 2.0.6 of the hdp plugin::

  $ sahara-templates --config-file myconfig update -t $TENANT_ID -p vanilla -pv vanilla.2.7.1 -p hdp -pv hdp.2.0.6

Delete default templates for the vanilla plugin::

  $ sahara-templates --config-file myconfig delete -t $TENANT_ID -p vanilla

Delete default templates for version 2.7.1 of the vanilla plugin::

  $ sahara-templates --config-file myconfig delete -t $TENANT_ID -p vanilla -pv 2.7.1

Delete a specific node group template by ID::

  $ sahara-templates --config-file myconfig node-group-template-delete-id --id ID

Delete a specific cluster template by ID::

  $ sahara-templates --config-file myconfig cluster-template-delete-id --id ID

Delete a specific node group template by name::

  $ sahara-templates --config-file myconfig node-group-template-delete --name NAME -t $TENANT_ID

Delete a specific cluster template by name::

  $ sahara-templates --config-file myconfig cluster-template-delete --name NAME -t $TENANT_ID
