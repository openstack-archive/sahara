Pluggable Provisioning Mechanism
================================

Sahara could be integrated with 3rd party management tools like Apache Ambari
and Cloudera Management Console. The integration is achieved using plugin
mechanism.

In short, responsibilities are divided between Sahara core and plugin as
follows. Sahara interacts with user and provisions infrastructure (VMs).
Plugin installs and configures Hadoop cluster on the VMs. Optionally Plugin
could deploy management and monitoring tools for the cluster. Sahara
provides plugin with utility methods to work with VMs.

A plugin must extend `sahara.plugins.provisioning:ProvisioningPluginBase`
class and implement all the required methods. Read :doc:`plugin.spi` for
details.

The `instance` objects provided by Sahara have `remote` property which
could be used to work with VM. The `remote` is a context manager so you
can use it in `with instance.remote:` statements. The list of available
commands could be found in `sahara.utils.remote.InstanceInteropHelper`.
See Vanilla plugin source for usage examples.
