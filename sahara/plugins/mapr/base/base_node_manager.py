# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import json
import random

from oslo_log import log as logging
from oslo_utils import timeutils

from sahara import context
from sahara.i18n import _
from sahara.i18n import _LI
import sahara.plugins.exceptions as ex
import sahara.plugins.mapr.abstract.node_manager as s
import sahara.plugins.mapr.services.management.management as mng
import sahara.plugins.mapr.services.maprfs.maprfs as mfs


LOG = logging.getLogger(__name__)


GET_SERVER_ID_CMD = ('maprcli node list -json -filter [ip==%s] -columns id'
                     ' | grep id | grep -o \'[0-9]*\'')
NODE_LIST_CMD = 'maprcli node list -json'
MOVE_NODE_CMD = 'maprcli node move -serverids %s -topology /decommissioned'
REMOVE_NODE_CMD = ('maprcli node remove -filter [ip==%(ip)s] -nodes %(nodes)s'
                   ' -zkconnect %(zookeepers)s')
WAIT_NODE_ALARM_NO_HEARTBEAT = 360

WARDEN_SERVICE = 'warden'
START = 'start'
STOP = 'stop'
DELAY = 5
DEFAULT_RETRY_COUNT = 10


class BaseNodeManager(s.AbstractNodeManager):
    def move_nodes(self, cluster_context, instances):
        LOG.debug("Moving the nodes to /decommissioned topology")
        cldb_instances = self._get_cldb_instances(cluster_context, instances)
        with random.choice(cldb_instances).remote() as cldb_remote:
            for instance in instances:
                with instance.remote() as r:
                    command = GET_SERVER_ID_CMD % instance.management_ip
                    ec, out = r.execute_command(command, run_as_root=True)
                    command = MOVE_NODE_CMD % out.strip()
                    cldb_remote.execute_command(command, run_as_root=True)
        LOG.info(_LI("Nodes successfully moved"))

    def remove_nodes(self, c_context, instances):
        LOG.debug("Removing nodes from cluster")
        cldb_instances = self._get_cldb_instances(c_context, instances)
        with random.choice(cldb_instances).remote() as cldb_remote:
            for instance in instances:
                args = {
                    'ip': instance.management_ip,
                    'nodes': instance.fqdn(),
                    'zookeepers': c_context.get_zookeeper_nodes_ip_with_port(),
                }
                command = REMOVE_NODE_CMD % args
                cldb_remote.execute_command(command, run_as_root=True)
        LOG.info(_LI("Nodes successfully removed"))

    def start(self, cluster_context, instances=None):
        instances = instances or cluster_context.get_instances()
        zookeepers = cluster_context.filter_instances(instances, mng.ZOOKEEPER)
        cldbs = cluster_context.filter_instances(instances, mfs.CLDB)
        others = filter(
            lambda i: not cluster_context.check_for_process(i, mfs.CLDB),
            instances)
        self._start_zk_nodes(zookeepers)
        self._start_cldb_nodes(cldbs)
        self._start_non_cldb_nodes(others)
        self._await_cldb(cluster_context, instances)

    def stop(self, cluster_context, instances=None):
        instances = instances or cluster_context.get_instances()
        zookeepers = cluster_context.filter_instances(instances, mng.ZOOKEEPER)
        self._stop_zk_nodes(zookeepers)
        self._stop_warden_on_nodes(instances)

    def _await_cldb(self, cluster_context, instances=None, timeout=600):
        instances = instances or cluster_context.get_instances()
        cldb_node = cluster_context.get_instance(mfs.CLDB)
        start_time = timeutils.utcnow()
        retry_count = 0
        with cldb_node.remote() as r:
            LOG.debug("Waiting {count} seconds for CLDB initialization".format(
                count=timeout))
            while timeutils.delta_seconds(start_time,
                                          timeutils.utcnow()) < timeout:
                ec, out = r.execute_command(NODE_LIST_CMD,
                                            raise_when_error=False)
                resp = json.loads(out)
                status = resp['status']
                if str(status).lower() == 'ok':
                    ips = [n['ip'] for n in resp['data']]
                    retry_count += 1
                    for i in instances:
                        if (i.management_ip not in ips
                                and retry_count > DEFAULT_RETRY_COUNT):
                            raise ex.HadoopProvisionError(_(
                                "Node failed to connect to CLDB: %s") %
                                i.management_ip)
                    break
                else:
                    context.sleep(DELAY)
            else:
                raise ex.HadoopProvisionError(_("CLDB failed to start"))

    def _start_nodes(self, instances, sys_service):
        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('start-%s-%s' % (sys_service, instance.id),
                         self._start_service, instance, sys_service)

    def _stop_nodes(self, instances, sys_service):
        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('stop-%s-%s' % (sys_service, instance.id),
                         self._stop_service, instance, sys_service)

    def _start_zk_nodes(self, instances):
        LOG.debug('Starting ZooKeeper nodes')
        self._start_nodes(instances, mng.ZOOKEEPER.ui_name)
        LOG.info(_LI('ZooKeeper nodes successfully started'))

    def _start_cldb_nodes(self, instances):
        LOG.debug('Starting CLDB nodes')
        self._start_nodes(instances, WARDEN_SERVICE)
        LOG.info(_LI('CLDB nodes successfully started'))

    def _start_non_cldb_nodes(self, instances):
        LOG.debug('Starting non-control nodes')
        self._start_nodes(instances, WARDEN_SERVICE)
        LOG.info(_LI('Non-control nodes successfully started'))

    def _stop_zk_nodes(self, instances):
        self._stop_nodes(instances, mng.ZOOKEEPER.ui_name)

    def _stop_warden_on_nodes(self, instances):
        self._stop_nodes(instances, WARDEN_SERVICE)

    @staticmethod
    def _do_service_action(instance, service, action):
        with instance.remote() as r:
            cmd = "service mapr-%(service)s %(action)s"
            args = {'service': service.lower(), 'action': action}
            cmd = cmd % args
            LOG.debug(
                'Executing "{command}" on node={ip}'.format(
                    command=cmd, ip=instance.management_ip))
            r.execute_command(cmd, run_as_root=True)

    def _start_service(self, instance, service):
        return self._do_service_action(instance, service, START)

    def _stop_service(self, instance, service):
        return self._do_service_action(instance, service, STOP)

    def _get_cldb_instances(self, c_context, instances):
        current = self._get_current_cluster_instances(c_context, instances)
        return c_context.filter_instances(current, mfs.CLDB)

    @staticmethod
    def await_no_heartbeat():
        delay = WAIT_NODE_ALARM_NO_HEARTBEAT
        LOG.debug('Waiting for "NO_HEARBEAT" alarm')
        context.sleep(delay)

    def _get_current_cluster_instances(self, cluster_context, instances):
        all_instances = cluster_context.get_instances()
        return [x for x in all_instances if x not in instances]
