Pluggable Provisioning Mechanism
================================

Sahara can be integrated with 3rd party management tools like Apache Ambari
and Cloudera Management Console. The integration is achieved using the plugin
mechanism.

In short, responsibilities are divided between the Sahara core and a plugin as
follows. Sahara interacts with the user and uses Heat to provision OpenStack
resources (VMs, baremetal servers, security groups, etc.) The plugin installs
and configures a Hadoop cluster on the provisioned instances. Optionally,
a plugin can deploy management and monitoring tools for the cluster. Sahara
provides plugins with utility methods to work with provisioned instances.

A plugin must extend the `sahara.plugins.provisioning:ProvisioningPluginBase`
class and implement all the required methods. Read :doc:`plugin-spi` for
details.

The `instance` objects provided by Sahara have a `remote` property which
can be used to interact with instances. The `remote` is a context manager so
you can use it in `with instance.remote:` statements. The list of available
commands can be found in `sahara.utils.remote.InstanceInteropHelper`.
See the source code of the Vanilla plugin for usage examples.
