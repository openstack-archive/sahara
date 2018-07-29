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

from oslo_config import cfg
from oslo_log import log as logging
import six

from sahara import conductor as c
from sahara import context
from sahara.i18n import _
from sahara.service import networks
from sahara.utils import cluster as cluster_utils
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import edp
from sahara.utils.openstack import base as b
from sahara.utils.openstack import images as sahara_images
from sahara.utils import poll_utils
from sahara.utils import remote

LOG = logging.getLogger(__name__)
conductor = c.API
CONF = cfg.CONF


@six.add_metaclass(abc.ABCMeta)
class Engine(object):

    @abc.abstractmethod
    def create_cluster(self, cluster):
        pass

    @abc.abstractmethod
    def scale_cluster(self, cluster, node_group_id_map):
        pass

    @abc.abstractmethod
    def shutdown_cluster(self, cluster, force):
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

        LOG.info("All instances have IPs assigned")

        cluster = conductor.cluster_get(context.ctx(), cluster)
        instances = cluster_utils.get_instances(cluster, ips_assigned)

        cpo.add_provisioning_step(
            cluster.id, _("Wait for instance accessibility"), len(instances))

        with context.ThreadGroup() as tg:
            for instance in instances:
                with context.set_current_instance_id(instance.instance_id):
                    tg.spawn("wait-for-ssh-%s" % instance.instance_name,
                             self._wait_until_accessible, instance)

        LOG.info("All instances are accessible")

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
            ip_used = "internal_ip" if CONF.proxy_command and \
                CONF.proxy_command_use_internal_ip else "management_ip"
            LOG.debug("Can't login to node, IP: {ip}, reason {reason}"
                      .format(ip=getattr(instance, ip_used),
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
        hostname = instance.fqdn()
        with instance.remote() as r:
            r.write_file_to('etc-hosts', hosts_file)
            r.write_file_to('etc-hostname', hostname)
            r.execute_command('sudo hostname %s' % hostname)
            r.execute_command('sudo cp etc-hosts /etc/hosts')
            r.execute_command('sudo cp etc-hostname /etc/hostname')
            r.execute_command('sudo rm etc-hosts  etc-hostname')
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

    def _remove_db_objects(self, cluster):
        ctx = context.ctx()
        cluster = conductor.cluster_get(ctx, cluster)
        instances = cluster_utils.get_instances(cluster)
        for inst in instances:
            conductor.instance_remove(ctx, inst)
