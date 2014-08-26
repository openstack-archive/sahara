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

import six

from sahara import conductor as c
from sahara import context
from sahara.i18n import _LI
from sahara.i18n import _LW
from sahara.openstack.common import log as logging
from sahara.service import networks
from sahara.utils import edp
from sahara.utils import general as g
from sahara.utils.openstack import nova
from sahara.utils import remote


LOG = logging.getLogger(__name__)
conductor = c.API


@six.add_metaclass(abc.ABCMeta)
class Engine:
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
        return nova.client().images.get(image_id).username

    def _await_networks(self, cluster, instances):
        if not instances:
            return

        ips_assigned = set()
        while len(ips_assigned) != len(instances):
            if not g.check_cluster_exists(cluster):
                return
            for instance in instances:
                if instance.id not in ips_assigned:
                    if networks.init_instances_ips(instance):
                        ips_assigned.add(instance.id)

            context.sleep(1)

        LOG.info(
            _LI("Cluster '%s': all instances have IPs assigned"), cluster.id)

        cluster = conductor.cluster_get(context.ctx(), cluster)
        instances = g.get_instances(cluster, ips_assigned)

        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn("wait-for-ssh-%s" % instance.instance_name,
                         self._wait_until_accessible, instance)

        LOG.info(_LI("Cluster '%s': all instances are accessible"), cluster.id)

    def _wait_until_accessible(self, instance):
        while True:
            try:
                # check if ssh is accessible and cloud-init
                # script is finished generating authorized_keys
                exit_code, stdout = instance.remote().execute_command(
                    "ls .ssh/authorized_keys", raise_when_error=False)

                if exit_code == 0:
                    LOG.debug(
                        'Instance %s is accessible' % instance.instance_name)
                    return
            except Exception as ex:
                LOG.debug("Can't login to node %s (%s), reason %s",
                          instance.instance_name, instance.management_ip, ex)

            context.sleep(5)

            if not g.check_cluster_exists(instance.node_group.cluster):
                return

    def _configure_instances(self, cluster):
        """Configure active instances.

        * generate /etc/hosts
        * setup passwordless login
        * etc.
        """
        hosts_file = g.generate_etc_hosts(cluster)

        with context.ThreadGroup() as tg:
            for node_group in cluster.node_groups:
                for instance in node_group.instances:
                    tg.spawn("configure-instance-%s" % instance.instance_name,
                             self._configure_instance, instance, hosts_file)

    def _configure_instance(self, instance, hosts_file):
        LOG.debug('Configuring instance %s' % instance.instance_name)

        with instance.remote() as r:
            r.write_file_to('etc-hosts', hosts_file)
            r.execute_command('sudo hostname %s' % instance.fqdn())
            r.execute_command('sudo mv etc-hosts /etc/hosts')

            r.execute_command('sudo usermod -s /bin/bash $USER')

    def _generate_user_data_script(self, node_group, instance_name):
        script = """#!/bin/bash
echo "${public_key}" >> ${user_home}/.ssh/authorized_keys\n
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

    def _log_operation_exception(self, message, cluster, ex):
        # we want to log the initial exception even if cluster was deleted
        cluster_name = cluster.name if cluster is not None else '_unknown_'
        LOG.warn(message, {'cluster': cluster_name, 'reason': ex})
        if cluster is None:
            LOG.warn(
                _LW("Presumably the operation failed because the cluster was "
                    "deleted by a user during the process."))
