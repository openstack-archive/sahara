# Copyright (c) 2014 Hoang Do, Phuc Vo, P. Michiardi, D. Venzano
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

from oslo_config import cfg
from oslo_log import log as logging
import six
import yaml

from sahara import conductor
from sahara import context
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.plugins import exceptions as ex
from sahara.plugins import provisioning as p
from sahara.plugins.storm import config_helper as c_helper
from sahara.plugins.storm import edp_engine
from sahara.plugins.storm import run_scripts as run
from sahara.plugins import utils
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import general as ug
from sahara.utils import remote

conductor = conductor.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class StormProvider(p.ProvisioningPluginBase):
    def __init__(self):
        self.processes = {
            "Zookeeper": ["zookeeper"],
            "Storm": ["nimbus", "supervisor"]
        }

    def get_title(self):
        return "Apache Storm"

    def get_description(self):
        return (
            _("This plugin provides an ability to launch Storm "
              "cluster without any management consoles."))

    def get_versions(self):
        return ['0.9.2', '1.0.1']

    def get_configs(self, storm_version):
        return c_helper.get_plugin_configs()

    def get_node_processes(self, storm_version):
        return self.processes

    def validate(self, cluster):
        # validate Storm Master Node and Storm Slaves
        sm_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "nimbus")])

        if sm_count != 1:
            raise ex.RequiredServiceMissingException("Storm nimbus")

        sl_count = sum([ng.count for ng
                        in utils.get_node_groups(cluster, "supervisor")])

        if sl_count < 1:
            raise ex.InvalidComponentCountException("Storm supervisor",
                                                    _("1 or more"),
                                                    sl_count)

    def update_infra(self, cluster):
        pass

    def configure_cluster(self, cluster):
        self._setup_instances(cluster)

    def start_cluster(self, cluster):
        sm_instance = utils.get_instance(cluster, "nimbus")
        sl_instances = utils.get_instances(cluster, "supervisor")
        zk_instances = utils.get_instances(cluster, "zookeeper")

        # start zookeeper processes
        self._start_zookeeper_processes(zk_instances)

        # start storm master
        if sm_instance:
            self._start_storm_master(sm_instance)

        # start storm slaves
        self._start_slave_processes(sl_instances)

        LOG.info(_LI('Cluster {cluster} has been started successfully').format(
                 cluster=cluster.name))
        self._set_cluster_info(cluster)

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp_engine.EdpEngine.get_supported_job_types():
            return edp_engine.EdpEngine(cluster)

        return None

    def get_edp_job_types(self, versions=None):
        res = {}
        for vers in self.get_versions():
            if not versions or vers in versions:
                if edp_engine.EdpEngine.edp_supported(vers):
                    res[vers] = edp_engine.EdpEngine.get_supported_job_types()
        return res

    def get_edp_config_hints(self, job_type, version):
        if edp_engine.EdpEngine.edp_supported(version):
            return edp_engine.EdpEngine.get_possible_job_config(job_type)
        return {}

    def get_open_ports(self, node_group):
        ports_map = {
            'nimbus': [8080]
        }

        ports = []
        for process in node_group.node_processes:
            if process in ports_map:
                ports.extend(ports_map[process])

        return ports

    def _extract_configs_to_extra(self, cluster):
        st_master = utils.get_instance(cluster, "nimbus")
        zk_servers = utils.get_instances(cluster, "zookeeper")

        extra = dict()

        config_instances = ''
        if st_master is not None:
            if zk_servers is not None:
                zknames = []
                for zk in zk_servers:
                    zknames.append(zk.hostname())

            config_instances = c_helper.generate_storm_config(
                st_master.hostname(),
                zknames,
                cluster.hadoop_version)

        config = self._convert_dict_to_yaml(config_instances)
        supervisor_conf = c_helper.generate_slave_supervisor_conf()
        nimbus_ui_conf = c_helper.generate_master_supervisor_conf()
        zk_conf = c_helper.generate_zookeeper_conf()

        for ng in cluster.node_groups:
            extra[ng.id] = {
                'st_instances': config,
                'slave_sv_conf': supervisor_conf,
                'master_sv_conf': nimbus_ui_conf,
                'zk_conf': zk_conf
            }

        return extra

    @cpo.event_wrapper(
        True, step=utils.start_process_event_message("StormMaster"))
    def _start_storm_master(self, sm_instance):
        with remote.get_remote(sm_instance) as r:
            run.start_storm_nimbus_and_ui(r)
            LOG.info(_LI("Storm master at {host} has been started").format(
                     host=sm_instance.hostname()))

    def _start_slave_processes(self, sl_instances):
        if len(sl_instances) == 0:
            return
        cpo.add_provisioning_step(
            sl_instances[0].cluster_id,
            utils.start_process_event_message("Slave"), len(sl_instances))

        with context.ThreadGroup() as tg:
            for i in sl_instances:
                tg.spawn('storm-start-sl-%s' % i.instance_name,
                         self._start_slaves, i)

    @cpo.event_wrapper(True)
    def _start_slaves(self, instance):
        with instance.remote() as r:
            run.start_storm_supervisor(r)

    def _start_zookeeper_processes(self, zk_instances):
        if len(zk_instances) == 0:
            return

        cpo.add_provisioning_step(
            zk_instances[0].cluster_id,
            utils.start_process_event_message("Zookeeper"), len(zk_instances))

        with context.ThreadGroup() as tg:
            for i in zk_instances:
                tg.spawn('storm-start-zk-%s' % i.instance_name,
                         self._start_zookeeper, i)

    @cpo.event_wrapper(True)
    def _start_zookeeper(self, instance):
        with instance.remote() as r:
            run.start_zookeeper(r)

    def _setup_instances(self, cluster, instances=None):
        extra = self._extract_configs_to_extra(cluster)

        if instances is None:
            instances = utils.get_instances(cluster)

        self._push_configs_to_nodes(cluster, extra, instances)

    def _push_configs_to_nodes(self, cluster, extra, new_instances):
        all_instances = utils.get_instances(cluster)
        cpo.add_provisioning_step(
            cluster.id, _("Push configs to nodes"), len(all_instances))

        with context.ThreadGroup() as tg:
            for instance in all_instances:
                if instance in new_instances:
                    tg.spawn('storm-configure-%s' % instance.instance_name,
                             self._push_configs_to_new_node, cluster,
                             extra, instance)
                else:
                    tg.spawn('storm-reconfigure-%s' % instance.instance_name,
                             self._push_configs_to_existing_node, cluster,
                             extra, instance)

    def _convert_dict_to_yaml(self, dict_to_convert):
        new_dict = dict_to_convert.copy()
        for key in dict_to_convert:
            if isinstance(dict_to_convert[key], six.string_types):
                new_dict[key] = "\"" + dict_to_convert[key] + "\""

        stream = yaml.dump(new_dict, default_flow_style=False)
        stream = stream.replace("\'", "")

        return stream

    @cpo.event_wrapper(True)
    def _push_configs_to_new_node(self, cluster, extra, instance):
        ng_extra = extra[instance.node_group.id]

        files_supervisor = {
            '/etc/supervisor/supervisord.conf': ng_extra['slave_sv_conf']
        }
        files_storm = {
            '/usr/local/storm/conf/storm.yaml': ng_extra['st_instances']
        }
        files_zk = {
            '/opt/zookeeper/zookeeper/conf/zoo.cfg': ng_extra['zk_conf']
        }
        files_supervisor_master = {
            '/etc/supervisor/supervisord.conf': ng_extra['master_sv_conf']
        }

        with remote.get_remote(instance) as r:
            node_processes = instance.node_group.node_processes
            r.write_files_to(files_storm, run_as_root=True)
            if 'zookeeper' in node_processes:
                self._push_zk_configs(r, files_zk)
            if 'nimbus' in node_processes:
                self._push_supervisor_configs(r, files_supervisor_master)
            if 'supervisor' in node_processes:
                self._push_supervisor_configs(r, files_supervisor)

    @cpo.event_wrapper(True)
    def _push_configs_to_existing_node(self, cluster, extra, instance):
        node_processes = instance.node_group.node_processes
        need_storm_update = ('nimbus' in node_processes or
                             'supervisor' in node_processes)
        need_zookeeper_update = 'zookeeper' in node_processes

        ng_extra = extra[instance.node_group.id]
        r = remote.get_remote(instance)

        if need_storm_update:
            storm_path = '/usr/local/storm/conf/storm.yaml'
            files_storm = {storm_path: ng_extra['st_instances']}
            r.write_files_to(files_storm)

        if need_zookeeper_update:
            zk_path = '/opt/zookeeper/zookeeper-3.4.6/conf/zoo.cfg'
            files_zookeeper = {zk_path: ng_extra['zk_conf']}
            self._push_zk_configs(r, files_zookeeper)

    def _set_cluster_info(self, cluster):
        st_master = utils.get_instance(cluster, "nimbus")
        info = {}

        if st_master:
            port = "8080"

            info['Strom'] = {
                'Web UI': 'http://%s:%s' % (st_master.management_ip, port)
            }
        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster, {'info': info})

    def _push_zk_configs(self, r, files):
        r.write_files_to(files, run_as_root=True)

    def _push_supervisor_configs(self, r, files):
        r.append_to_files(files, run_as_root=True)

    # Scaling

    def _get_running_topologies_names(self, cluster):
        master = utils.get_instance(cluster, "nimbus")

        cmd = (
            "%(storm)s -c nimbus.host=%(host)s "
            "list | grep ACTIVE | awk '{print $1}'") % (
            {
                "storm": "/usr/local/storm/bin/storm",
                "host": master.hostname()
            })

        with remote.get_remote(master) as r:
            ret, stdout = r.execute_command(cmd)
        names = stdout.split('\n')
        topology_names = names[0:len(names)-1]
        return topology_names

    @cpo.event_wrapper(True, step=_("Rebalance Topology"),
                       param=('cluster', 1))
    def rebalance_topology(self, cluster):
        topology_names = self._get_running_topologies_names(cluster)
        master = utils.get_instance(cluster, "nimbus")

        for topology_name in topology_names:
            cmd = (
                '%(rebalance)s -c nimbus.host=%(host)s %(topology_name)s') % (
                {
                    "rebalance": "/usr/local/storm/bin/storm rebalance",
                    "host": master.hostname(),
                    "topology_name": topology_name
                })

            with remote.get_remote(master) as r:
                ret, stdout = r.execute_command(cmd)

    def validate_scaling(self, cluster, existing, additional):
        self._validate_existing_ng_scaling(cluster, existing)
        self._validate_additional_ng_scaling(cluster, additional)

    def scale_cluster(self, cluster, instances):
        self._setup_instances(cluster, instances)
        # start storm slaves
        self._start_slave_processes(instances)
        self.rebalance_topology(cluster)
        LOG.info(_LI("Storm scaling has been started."))

    def _get_scalable_processes(self):
        return ["supervisor"]

    def _validate_additional_ng_scaling(self, cluster, additional):
        scalable_processes = self._get_scalable_processes()

        for ng_id in additional:
            ng = ug.get_by_id(cluster.node_groups, ng_id)
            if not set(ng.node_processes).issubset(scalable_processes):
                raise ex.NodeGroupCannotBeScaled(
                    ng.name, _("Storm plugin cannot scale nodegroup"
                               " with processes: %s") %
                    ' '.join(ng.node_processes))

    def _validate_existing_ng_scaling(self, cluster, existing):
        scalable_processes = self._get_scalable_processes()
        for ng in cluster.node_groups:
            if ng.id in existing:
                if not set(ng.node_processes).issubset(scalable_processes):
                    raise ex.NodeGroupCannotBeScaled(
                        ng.name, _("Storm plugin cannot scale nodegroup"
                                   " with processes: %s") %
                        ' '.join(ng.node_processes))
