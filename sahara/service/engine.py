# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import abc
import datetime
import string

from novaclient import exceptions as nova_exceptions
from oslo_log import log as logging
import six

from sahara import conductor as c
from sahara import context
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.i18n import _LW
from sahara.service import networks
from sahara.service import volumes
from sahara.utils import cluster as cluster_utils
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import edp
from sahara.utils import general as g
from sahara.utils.openstack import base as b
from sahara.utils.openstack import images as sahara_images
from sahara.utils.openstack import nova
from sahara.utils import poll_utils
from sahara.utils import remote

LOG = logging.getLogger(__name__)
conductor = c.API


@six.add_metaclass(abc.ABCMeta)
class Engine(object):
    @abc.abstractmethod
    def create_cluster(self, cluster):
        pass

    @abc.abstractmethod
    def scale_cluster(self, cluster, node_group_id_map):
        pass

    @abc.abstractmethod
    def shutdown_cluster(self, cluster):
        pass

    @abc.abstractmethod
    def rollback_cluster(self, cluster, reason):
        pass

    @abc.abstractmethod
    def get_type_and_version(self):
        """Returns engine type and version

         Result should be in the form 'type.major.minor'.
         """

    def get_node_group_image_username(self, node_group):
        image_id = node_group.get_image_id()
        return b.execute_with_retries(
            sahara_images.image_manager().get, image_id).username

    @poll_utils.poll_status('ips_assign_timeout', _("Assign IPs"), sleep=1)
    def _ips_assign(self, ips_assigned, cluster, instances):
        if not cluster_utils.check_cluster_exists(cluster):
            return True
        for instance in instances:
            if instance.id not in ips_assigned:
                with context.set_current_instance_id(instance.instance_id):
                    if networks.init_instances_ips(instance):
                        ips_assigned.add(instance.id)
                        cpo.add_successful_event(instance)
        return len(ips_assigned) == len(instances)

    def _await_networks(self, cluster, instances):
        if not instances:
            return

        cpo.add_provisioning_step(cluster.id, _("Assign IPs"), len(instances))

        ips_assigned = set()
        self._ips_assign(ips_assigned, cluster, instances)

        LOG.info(
            _LI("All instances have IPs assigned"))

        cluster = conductor.cluster_get(context.ctx(), cluster)
        instances = cluster_utils.get_instances(cluster, ips_assigned)

        cpo.add_provisioning_step(
            cluster.id, _("Wait for instance accessibility"), len(instances))

        with context.ThreadGroup() as tg:
            for instance in instances:
                with context.set_current_instance_id(instance.instance_id):
                    tg.spawn("wait-for-ssh-%s" % instance.instance_name,
                             self._wait_until_accessible, instance)

        LOG.info(_LI("All instances are accessible"))

    @poll_utils.poll_status(
        'wait_until_accessible', _("Wait for instance accessibility"),
        sleep=5)
    def _is_accessible(self, instance):
        if not cluster_utils.check_cluster_exists(instance.cluster):
            return True
        try:
            # check if ssh is accessible and cloud-init
            # script is finished generating authorized_keys
            exit_code, stdout = instance.remote().execute_command(
                "ls .ssh/authorized_keys", raise_when_error=False)

            if exit_code == 0:
                LOG.debug('Instance is accessible')
                return True
        except Exception as ex:
            LOG.debug("Can't login to node, IP: {mgmt_ip}, "
                      "reason {reason}".format(mgmt_ip=instance.management_ip,
                                               reason=ex))
            return False

        return False

    @cpo.event_wrapper(mark_successful_on_exit=True)
    def _wait_until_accessible(self, instance):
        self._is_accessible(instance)

    def _configure_instances(self, cluster):
        """Configure active instances.

        * generate /etc/hosts
        * change /etc/resolv.conf
        * setup passwordless login
        * etc.
        """
        cpo.add_provisioning_step(
            cluster.id, _("Configure instances"),
            cluster_utils.count_instances(cluster))

        with context.ThreadGroup() as tg:
            for node_group in cluster.node_groups:
                for instance in node_group.instances:
                    with context.set_current_instance_id(instance.instance_id):
                        tg.spawn("configure-instance-{}".format(
                            instance.instance_name),
                            self._configure_instance, instance, cluster
                        )

    @cpo.event_wrapper(mark_successful_on_exit=True)
    def _configure_instance(self, instance, cluster):
        self._configure_instance_etc_hosts(instance, cluster)
        if cluster.use_designate_feature():
            self._configure_instance_resolve_conf(instance)

    def _configure_instance_etc_hosts(self, instance, cluster):
        LOG.debug('Configuring "/etc/hosts" of instance.')
        hosts_file = cluster_utils.generate_etc_hosts(cluster)
        with instance.remote() as r:
            r.write_file_to('etc-hosts', hosts_file)
            r.execute_command('sudo hostname %s' % instance.fqdn())
            r.execute_command('sudo mv etc-hosts /etc/hosts')

            r.execute_command('sudo usermod -s /bin/bash $USER')

    def _configure_instance_resolve_conf(self, instance):
        LOG.debug('Setting up those name servers from sahara.conf '
                  'which are lacked in the /etc/resolv.conf.')
        with instance.remote() as r:
            code, curr_resolv_conf = r.execute_command('cat /etc/resolv.conf')
            diff = cluster_utils.generate_resolv_conf_diff(curr_resolv_conf)
            if diff.strip():
                position = curr_resolv_conf.find('nameserver')
                if position == -1:
                    position = 0
                new_resolv_conf = "{}\n{}{}".format(
                    curr_resolv_conf[:position],
                    diff,
                    curr_resolv_conf[position:])
                r.write_file_to('resolv-conf', new_resolv_conf)
                r.execute_command('sudo mv resolv-conf /etc/resolv.conf')

    def _generate_user_data_script(self, node_group, instance_name):
        script = """#!/bin/bash
echo "${public_key}" >> ${user_home}/.ssh/authorized_keys\n
# ====== COMMENT OUT Defaults requiretty in /etc/sudoers ========
sed '/^Defaults    requiretty*/ s/^/#/' -i /etc/sudoers\n
"""

        script += remote.get_userdata_template()

        username = node_group.image_username

        if username == "root":
            user_home = "/root/"
        else:
            user_home = "/home/%s/" % username

        script_template = string.Template(script)

        return script_template.safe_substitute(
            public_key=node_group.cluster.management_public_key,
            user_home=user_home,
            instance_name=instance_name)

    # Deletion ops
    def _clean_job_executions(self, cluster):
        ctx = context.ctx()
        for je in conductor.job_execution_get_all(ctx, cluster_id=cluster.id):
            update = {"cluster_id": None}
            if not je.end_time:
                info = je.info.copy() if je.info else {}
                info['status'] = edp.JOB_STATUS_KILLED
                update.update({"info": info,
                               "end_time": datetime.datetime.now()})
            conductor.job_execution_update(ctx, je, update)

    def _delete_auto_security_group(self, node_group):
        if not node_group.auto_security_group:
            return

        if not node_group.security_groups:
            # node group has no security groups
            # nothing to delete
            return

        name = node_group.security_groups[-1]

        try:
            client = nova.client().security_groups
            security_group = b.execute_with_retries(client.get, name)
            if (security_group.name !=
                    g.generate_auto_security_group_name(node_group)):
                LOG.warning(_LW("Auto security group for node group {name} is "
                                "not found").format(name=node_group.name))
                return
            b.execute_with_retries(client.delete, name)
        except Exception:
            LOG.warning(_LW("Failed to delete security group {name}").format(
                name=name))

    def _delete_aa_server_group(self, cluster):
        if cluster.anti_affinity:
            server_group_name = g.generate_aa_group_name(cluster.name)
            client = nova.client().server_groups

            server_groups = b.execute_with_retries(client.findall,
                                                   name=server_group_name)
            if len(server_groups) == 1:
                b.execute_with_retries(client.delete, server_groups[0].id)

    def _shutdown_instance(self, instance):
        # tmckay-fp perfect, already testing the right thing
        if instance.node_group.floating_ip_pool:
            try:
                b.execute_with_retries(networks.delete_floating_ip,
                                       instance.instance_id)
            except nova_exceptions.NotFound:
                LOG.warning(_LW("Attempted to delete non-existent floating IP "
                                "in pool {pool} from instance")
                            .format(pool=instance.node_group.floating_ip_pool))

        try:
            volumes.detach_from_instance(instance)
        except Exception:
            LOG.warning(_LW("Detaching volumes from instance failed"))

        try:
            b.execute_with_retries(nova.client().servers.delete,
                                   instance.instance_id)
        except nova_exceptions.NotFound:
            LOG.warning(_LW("Attempted to delete non-existent instance"))

        conductor.instance_remove(context.ctx(), instance)

    @cpo.event_wrapper(mark_successful_on_exit=False)
    def _check_if_deleted(self, instance):
        try:
            nova.get_instance_info(instance)
        except nova_exceptions.NotFound:
            return True

        return False

    @poll_utils.poll_status(
        'delete_instances_timeout',
        _("Wait for instances to be deleted"), sleep=1)
    def _check_deleted(self, deleted_ids, cluster, instances):
        if not cluster_utils.check_cluster_exists(cluster):
            return True

        for instance in instances:
            if instance.id not in deleted_ids:
                with context.set_current_instance_id(instance.instance_id):
                    if self._check_if_deleted(instance):
                        LOG.debug("Instance is deleted")
                        deleted_ids.add(instance.id)
                        cpo.add_successful_event(instance)
        return len(deleted_ids) == len(instances)

    def _await_deleted(self, cluster, instances):
        """Await all instances are deleted."""
        if not instances:
            return
        cpo.add_provisioning_step(
            cluster.id, _("Wait for instances to be deleted"), len(instances))

        deleted_ids = set()
        self._check_deleted(deleted_ids, cluster, instances)

    def _shutdown_instances(self, cluster):
        for node_group in cluster.node_groups:
            for instance in node_group.instances:
                with context.set_current_instance_id(instance.instance_id):
                    self._shutdown_instance(instance)

            self._await_deleted(cluster, node_group.instances)
            self._delete_auto_security_group(node_group)

    def _remove_db_objects(self, cluster):
        ctx = context.ctx()
        cluster = conductor.cluster_get(ctx, cluster)
        instances = cluster_utils.get_instances(cluster)
        for inst in instances:
            conductor.instance_remove(ctx, inst)
