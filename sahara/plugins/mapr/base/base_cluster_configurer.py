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


import abc
import os

from oslo_log import log as logging
import six

from sahara import conductor
from sahara import context
import sahara.plugins.mapr.abstract.configurer as ac
import sahara.plugins.mapr.services.management.management as mng
import sahara.plugins.mapr.services.mapreduce.mapreduce as mr
from sahara.plugins.mapr.services.maprfs import maprfs
from sahara.plugins.mapr.services.mysql import mysql
import sahara.plugins.mapr.services.yarn.yarn as yarn
import sahara.plugins.mapr.util.general as util
from sahara.topology import topology_helper as th
import sahara.utils.configs as sahara_configs
from sahara.utils import files as f


LOG = logging.getLogger(__name__)
conductor = conductor.API

MAPR_REPO_DIR = '/opt/mapr-repository'
_MAPR_HOME = '/opt/mapr'
_JAVA_HOME = '/usr/java/jdk1.7.0_51'
_CONFIGURE_SH_TIMEOUT = 600
_SET_MODE_CMD = 'maprcli cluster mapreduce set -mode '

_TOPO_SCRIPT = 'plugins/mapr/resources/topology.sh'

SERVICE_INSTALL_PRIORITY = [
    mng.Management(),
    yarn.YARNv251(),
    yarn.YARNv241(),
    mr.MapReduce(),
    maprfs.MapRFS(),
]


@six.add_metaclass(abc.ABCMeta)
class BaseConfigurer(ac.AbstractConfigurer):
    def configure(self, cluster_context, instances=None):
        instances = instances or cluster_context.get_instances()
        self._configure_ssh_connection(cluster_context, instances)
        self._install_mapr_repo(cluster_context, instances)
        self._install_services(cluster_context, instances)
        self._configure_topology(cluster_context, instances)
        self._configure_database(cluster_context, instances)
        self._configure_services(cluster_context, instances)
        self._configure_sh_cluster(cluster_context, instances)
        self._set_cluster_mode(cluster_context)
        self._write_config_files(cluster_context, instances)
        self._configure_environment(cluster_context, instances)
        self._update_cluster_info(cluster_context)

    def update(self, cluster_context, instances=None):
        LOG.debug('Configuring existing instances')
        instances = instances or cluster_context.get_instances()
        existing = cluster_context.existing_instances()
        self._configure_topology(cluster_context, existing)
        if cluster_context.has_control_nodes(instances):
            self._configure_sh_cluster(cluster_context, existing)
        self._write_config_files(cluster_context, existing)
        self._update_services(cluster_context, existing)
        self._restart_services(cluster_context)
        LOG.debug('Existing instances successfully configured')

    def _configure_services(self, cluster_context, instances):
        for service in cluster_context.cluster_services:
            service.configure(cluster_context, instances)

    def _install_services(self, cluster_context, instances):
        for service in self._service_install_sequence(cluster_context):
            service.install(cluster_context, instances)

    def _service_install_sequence(self, cluster_context):
        def key(service):
            if service in SERVICE_INSTALL_PRIORITY:
                return SERVICE_INSTALL_PRIORITY.index(service)
            return -1

        return sorted(cluster_context.cluster_services, key=key, reverse=True)

    def _configure_topology(self, context, instances):
        LOG.debug('Configuring cluster topology')
        is_node_aware = context.is_node_aware
        if is_node_aware:
            topo = th.generate_topology_map(context.cluster, is_node_aware)
            topo = '\n'.join(['%s %s' % i for i in six.iteritems(topo)])
            data_path = '%s/topology.data' % context.mapr_home
            script_path = '%s/topology.sh' % context.mapr_home
            files = {
                data_path: topo,
                script_path: f.get_file_text(_TOPO_SCRIPT),
            }
            chmod_cmd = 'chmod +x %s' % script_path
            for instance in instances:
                with instance.remote() as r:
                    r.write_files_to(files, run_as_root=True)
                    r.execute_command(chmod_cmd, run_as_root=True)
        else:
            LOG.debug('Data locality is disabled.')
        LOG.debug('Cluster topology successfully configured')

    def _execute_on_instances(self, function, cluster_context, instances,
                              **kwargs):
        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('%s-execution' % function.__name__,
                         function, instance, **kwargs)

    def _write_config_files(self, cluster_context, instances):
        LOG.debug('Writing config files')

        def get_node_groups(instances):
            return util.unique_list(instances, lambda i: i.node_group)

        for ng in get_node_groups(instances):
            ng_services = cluster_context.get_cluster_services(ng)
            ng_user_configs = ng.configuration()
            ng_default_configs = cluster_context.get_services_configs_dict(
                ng_services)
            ng_configs = sahara_configs.merge_configs(
                ng_default_configs, ng_user_configs)
            ng_config_files = dict()
            for service in ng_services:
                service_conf_files = service.get_config_files(
                    cluster_context=cluster_context,
                    configs=ng_configs[service.ui_name],
                    instance=ng.instances[0]
                )
                LOG.debug('Rendering %s config files', service.ui_name)
                for conf_file in service_conf_files:
                    ng_config_files.update({
                        conf_file.remote_path: conf_file.render()
                    })

            ng_instances = filter(lambda i: i in instances, ng.instances)
            self._write_ng_config_files(ng_instances, ng_config_files)
        LOG.debug('Config files successfully written')

    def _write_ng_config_files(self, instances, conf_files):
        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('write-config-files-%s' % instance.id,
                         self._write_config_files_instance, instance,
                         conf_files)

    def _configure_environment(self, cluster_context, instances):
        self.configure_general_environment(cluster_context, instances)
        self._post_install_services(cluster_context, instances)

    def _configure_database(self, cluster_context, instances):
        mysql_instance = mysql.MySQL.get_db_instance(cluster_context)
        distro_name = cluster_context.distro.name
        mysql.MySQL.install_mysql(mysql_instance, distro_name)
        mysql.MySQL.start_mysql_server(cluster_context)
        mysql.MySQL.create_databases(cluster_context, instances)

    @staticmethod
    def _write_config_files_instance(instance, config_files):
        paths = six.iterkeys(config_files)
        with instance.remote() as r:
            for path in paths:
                r.execute_command('mkdir -p ' + os.path.dirname(path),
                                  run_as_root=True)
            r.write_files_to(config_files, run_as_root=True)

    def _post_install_services(self, cluster_context, instances):
        LOG.debug('Executing service post install hooks')
        for s in cluster_context.cluster_services:
            s.post_install(cluster_context, instances)
        LOG.debug('Post install hooks execution successfully executed')

    def _update_cluster_info(self, cluster_context):
        LOG.debug('Updating UI information.')
        info = dict()
        for service in cluster_context.cluster_services:
            for uri_info in service.ui_info:
                title, process, url = uri_info
                info.update({
                    title: {
                        'WebUI': url % cluster_context.get_instance_ip(process)
                    }
                })

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster_context.cluster, {'info': info})

    def configure_general_environment(self, cluster_context, instances=None):
        LOG.debug('Executing post configure hooks')

        if not instances:
            instances = cluster_context.get_instances()

        def set_user_password(instance):
            LOG.debug('Setting password for user "mapr"')
            if self.mapr_user_exists(instance):
                with instance.remote() as r:
                    r.execute_command(
                        'echo "%s:%s"|chpasswd' % ('mapr', 'mapr'),
                        run_as_root=True)
            else:
                LOG.debug('user "mapr" does not exists')

        def create_home_mapr(instance):
            target_path = '/home/mapr'
            LOG.debug("Creating home directory for user 'mapr'")
            args = {'path': target_path}
            cmd = 'mkdir -p %(path)s && chown mapr:mapr %(path)s' % args
            if self.mapr_user_exists(instance):
                with instance.remote() as r:
                    r.execute_command(cmd, run_as_root=True)
            else:
                LOG.debug('user "mapr" does not exists')

        self._execute_on_instances(set_user_password, cluster_context,
                                   instances)
        self._execute_on_instances(create_home_mapr, cluster_context,
                                   instances)

    def _configure_sh_cluster(self, cluster_context, instances):
        LOG.debug('Executing configure.sh')

        if not instances:
            instances = cluster_context.get_instances()
        script = cluster_context.configure_sh

        db_specs = dict(mysql.MySQL.METRICS_SPECS._asdict())
        db_specs.update({
            'host': mysql.MySQL.get_db_instance(cluster_context).fqdn(),
            'port': mysql.MySQL.MYSQL_SERVER_PORT,
        })

        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('configure-sh-%s' % instance.id,
                         self._configure_sh_instance, cluster_context,
                         instance, script, db_specs)
        LOG.debug('Executing configure.sh successfully completed')

    def _configure_sh_instance(self, context, instance, command, specs):
        if not self.mapr_user_exists(instance):
            command += ' --create-user'
        if context.check_for_process(instance, mng.METRICS):
            command += (' -d %(host)s:%(port)s -du %(user)s -dp %(password)s '
                        '-ds %(db_name)s') % specs
        with instance.remote() as r:
            r.execute_command('sudo -i ' + command,
                              timeout=_CONFIGURE_SH_TIMEOUT)

    def _configure_ssh_connection(self, cluster_context, instances):
        def keep_alive_connection(instance):
            echo_param = 'echo "KeepAlive yes" >> ~/.ssh/config'
            echo_timeout = 'echo "ServerAliveInterval 60" >> ~/.ssh/config'
            with instance.remote() as r:
                r.execute_command(echo_param)
                r.execute_command(echo_timeout)

        self._execute_on_instances(keep_alive_connection,
                                   cluster_context, instances)

    def mapr_user_exists(self, instance):
            with instance.remote() as r:
                ec, out = r.execute_command(
                    'id -u mapr', run_as_root=True, raise_when_error=False)
            return ec == 0

    def post_start(self, c_context, instances=None):
        instances = instances or c_context.get_instances()
        LOG.debug('Executing service post start hooks')
        for service in c_context.cluster_services:
            updated = c_context.filter_instances(instances, service=service)
            service.post_start(c_context, updated)
        LOG.debug('Post start hooks execution successfully executed')

    def _set_cluster_mode(self, cluster_context):
        cluster_mode = cluster_context.cluster_mode
        if not cluster_mode:
            return
        cldb = cluster_context.get_instance(maprfs.CLDB)
        with cldb.remote() as r:
            cmd = 'sudo -u mapr maprcli cluster mapreduce set -mode %s'
            r.execute_command(cmd % cluster_mode)

    def _install_mapr_repo(self, cluster_context, instances):
        def add_repo(instance, **kwargs):
            with instance.remote() as r:
                script = '/tmp/repo_install.sh'
                data = cluster_context.get_install_repo_script_data()
                r.write_file_to(script, data, run_as_root=True)
                r.execute_command('chmod +x %s' % script, run_as_root=True)
                r.execute_command('%s %s' % (script, kwargs.get('distro')),
                                  run_as_root=True, raise_when_error=False)

        d_name = cluster_context.distro.name
        self._execute_on_instances(
            add_repo, cluster_context, instances, distro=d_name)

    def _update_services(self, c_context, instances):
        for service in c_context.cluster_services:
            updated = c_context.filter_instances(instances, service=service)
            service.update(c_context, updated)

    def _restart_services(self, cluster_context):
        restart = cluster_context.should_be_restarted
        for service, instances in six.iteritems(restart):
            service.restart(util.unique_list(instances))
