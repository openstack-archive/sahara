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

from oslo_log import log as logging
import six

from sahara import conductor
from sahara import context
from sahara.i18n import _
from sahara.i18n import _LI
from sahara.i18n import _LW
import sahara.plugins.mapr.abstract.configurer as ac
from sahara.plugins.mapr.domain import distro as d
from sahara.plugins.mapr.domain import service as srvc
import sahara.plugins.mapr.services.management.management as mng
import sahara.plugins.mapr.services.mapreduce.mapreduce as mr
from sahara.plugins.mapr.services.maprfs import maprfs
from sahara.plugins.mapr.services.mysql import mysql
import sahara.plugins.mapr.services.yarn.yarn as yarn
from sahara.plugins.mapr.util import event_log as el
import sahara.plugins.mapr.util.general as util
import sahara.plugins.mapr.util.password_utils as pu
import sahara.utils.files as files

LOG = logging.getLogger(__name__)
conductor = conductor.API

_JAVA_HOME = '/usr/java/jdk1.7.0_51'
_CONFIGURE_SH_TIMEOUT = 600
_SET_MODE_CMD = 'maprcli cluster mapreduce set -mode '

_TOPO_SCRIPT = 'plugins/mapr/resources/topology.sh'
INSTALL_JAVA_SCRIPT = 'plugins/mapr/resources/install_java.sh'
INSTALL_SCALA_SCRIPT = 'plugins/mapr/resources/install_scala.sh'
INSTALL_MYSQL_CLIENT = 'plugins/mapr/resources/install_mysql_client.sh'
ADD_MAPR_REPO_SCRIPT = 'plugins/mapr/resources/add_mapr_repo.sh'
ADD_SECURITY_REPO_SCRIPT = 'plugins/mapr/resources/add_security_repos.sh'

SERVICE_INSTALL_PRIORITY = [
    mng.Management(),
    yarn.YARNv251(),
    yarn.YARNv241(),
    yarn.YARNv270(),
    mr.MapReduce(),
    maprfs.MapRFS(),
]


@six.add_metaclass(abc.ABCMeta)
class BaseConfigurer(ac.AbstractConfigurer):
    def configure(self, cluster_context, instances=None):
        instances = instances or cluster_context.get_instances()
        self._configure_ssh_connection(cluster_context, instances)
        self._install_mapr_repo(cluster_context, instances)
        if not cluster_context.is_prebuilt:
            self._prepare_bare_image(cluster_context, instances)
        self._install_services(cluster_context, instances)
        if cluster_context.is_node_aware:
            self._configure_topology(cluster_context, instances)
        self._configure_database(cluster_context, instances)
        self._configure_services(cluster_context, instances)
        self._configure_sh_cluster(cluster_context, instances)
        self._set_cluster_mode(cluster_context, instances)
        self._post_configure_services(cluster_context, instances)
        self._write_config_files(cluster_context, instances)
        self._configure_environment(cluster_context, instances)
        self._update_cluster_info(cluster_context)

    def update(self, cluster_context, instances=None):
        LOG.debug('Configuring existing instances')
        instances = instances or cluster_context.get_instances()
        existing = cluster_context.existing_instances()
        if cluster_context.is_node_aware:
            self._configure_topology(cluster_context, existing)
        if cluster_context.has_control_nodes(instances):
            self._configure_sh_cluster(cluster_context, existing)
            self._post_configure_sh(cluster_context, existing)
        self._write_config_files(cluster_context, existing)
        self._update_services(cluster_context, existing)
        self._restart_services(cluster_context)
        self._update_cluster_info(cluster_context)
        LOG.info(_LI('Existing instances successfully configured'))

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
            return -service._priority

        return sorted(cluster_context.cluster_services, key=key, reverse=True)

    def _prepare_bare_image(self, cluster_context, instances):
        LOG.debug('Preparing bare image')
        if d.UBUNTU == cluster_context.distro:
            self._install_security_repos(cluster_context, instances)
        self._install_java(cluster_context, instances)
        self._install_scala(cluster_context, instances)
        self._install_mysql_client(cluster_context, instances)
        LOG.debug('Bare images successfully prepared')

    @el.provision_step(_("Install security repos"))
    def _install_security_repos(self, cluster_context, instances):
        LOG.debug("Installing security repos")

        @el.provision_event()
        def install_security_repos(instance):
            return util.run_script(instance, ADD_SECURITY_REPO_SCRIPT, "root")

        util.execute_on_instances(instances, install_security_repos)

    @el.provision_step(_("Install MySQL client"))
    def _install_mysql_client(self, cluster_context, instances):
        LOG.debug("Installing MySQL client")
        distro_name = cluster_context.distro.name

        @el.provision_event()
        def install_mysql_client(instance):
            return util.run_script(instance, INSTALL_MYSQL_CLIENT,
                                   "root", distro_name)

        util.execute_on_instances(instances, install_mysql_client)

    @el.provision_step(_("Install Scala"))
    def _install_scala(self, cluster_context, instances):
        LOG.debug("Installing Scala")
        distro_name = cluster_context.distro.name

        @el.provision_event()
        def install_scala(instance):
            return util.run_script(instance, INSTALL_SCALA_SCRIPT,
                                   "root", distro_name)

        util.execute_on_instances(instances, install_scala)

    @el.provision_step(_("Install Java"))
    def _install_java(self, cluster_context, instances):
        LOG.debug("Installing Java")
        distro_name = cluster_context.distro.name

        @el.provision_event()
        def install_java(instance):
            return util.run_script(instance, INSTALL_JAVA_SCRIPT,
                                   "root", distro_name)

        util.execute_on_instances(instances, install_java)

    @el.provision_step(_("Configure cluster topology"))
    def _configure_topology(self, cluster_context, instances):
        LOG.debug("Configuring cluster topology")

        topology_map = cluster_context.topology_map
        topology_map = ("%s %s" % item for item in six.iteritems(topology_map))
        topology_map = "\n".join(topology_map) + "\n"

        data_path = "%s/topology.data" % cluster_context.mapr_home
        script = files.get_file_text(_TOPO_SCRIPT)
        script_path = '%s/topology.sh' % cluster_context.mapr_home

        @el.provision_event()
        def write_topology_data(instance):
            util.write_file(instance, data_path, topology_map, owner="root")
            util.write_file(instance, script_path, script,
                            mode="+x", owner="root")

        util.execute_on_instances(instances, write_topology_data)

        LOG.info(_LI('Cluster topology successfully configured'))

    @el.provision_step(_("Write config files to instances"))
    def _write_config_files(self, cluster_context, instances):
        LOG.debug('Writing config files')

        @el.provision_event()
        def write_config_files(instance, config_files):
            for file in config_files:
                util.write_file(instance, file.path, file.data, mode=file.mode,
                                owner="mapr")

        node_groups = util.unique_list(instances, lambda i: i.node_group)
        for node_group in node_groups:
            config_files = cluster_context.get_config_files(node_group)
            ng_instances = [i for i in node_group.instances if i in instances]
            util.execute_on_instances(ng_instances, write_config_files,
                                      config_files=config_files)

        LOG.debug("Config files are successfully written")

    def _configure_environment(self, cluster_context, instances):
        self.configure_general_environment(cluster_context, instances)
        self._post_install_services(cluster_context, instances)

    def _configure_database(self, cluster_context, instances):
        mysql_instance = mysql.MySQL.get_db_instance(cluster_context)
        distro_name = cluster_context.distro.name
        mysql.MySQL.install_mysql(mysql_instance, distro_name)
        mysql.MySQL.start_mysql_server(cluster_context)
        mysql.MySQL.create_databases(cluster_context, instances)

    def _post_install_services(self, cluster_context, instances):
        LOG.debug('Executing service post install hooks')
        for s in cluster_context.cluster_services:
            s.post_install(cluster_context, instances)
        LOG.info(_LI('Post install hooks execution successfully executed'))

    def _update_cluster_info(self, cluster_context):
        LOG.debug('Updating UI information.')
        info = {'Admin user credentials': {'Username': 'mapr',
                                           'Password': pu.get_mapr_password
                                           (cluster_context.cluster)}}
        for service in cluster_context.cluster_services:
            for title, node_process, ui_info in (service.get_ui_info
                                                 (cluster_context)):
                removed = cluster_context.removed_instances(node_process)
                instances = cluster_context.get_instances(node_process)
                instances = [i for i in instances if i not in removed]

                if len(instances) == 1:
                    display_name_template = "%(title)s"
                else:
                    display_name_template = "%(title)s %(index)s"

                for index, instance in enumerate(instances, start=1):
                    args = {"title": title, "index": index}
                    display_name = display_name_template % args
                    data = ui_info.copy()
                    data[srvc.SERVICE_UI] = (data[srvc.SERVICE_UI] %
                                             instance.get_ip_or_dns_name())
                    info.update({display_name: data})

        ctx = context.ctx()
        conductor.cluster_update(ctx, cluster_context.cluster, {'info': info})

    def configure_general_environment(self, cluster_context, instances=None):
        LOG.debug('Executing post configure hooks')
        mapr_user_pass = pu.get_mapr_password(cluster_context.cluster)

        if not instances:
            instances = cluster_context.get_instances()

        def set_user_password(instance):
            LOG.debug('Setting password for user "mapr"')
            if self.mapr_user_exists(instance):
                with instance.remote() as r:
                    r.execute_command(
                        'echo "%s:%s"|chpasswd' %
                        ('mapr', mapr_user_pass),
                        run_as_root=True)
            else:
                LOG.warning(_LW('User "mapr" does not exists'))

        def create_home_mapr(instance):
            target_path = '/home/mapr'
            LOG.debug("Creating home directory for user 'mapr'")
            args = {'path': target_path,
                    'user': 'mapr',
                    'group': 'mapr'}
            cmd = ('mkdir -p %(path)s && chown %(user)s:%(group)s %(path)s'
                   % args)
            if self.mapr_user_exists(instance):
                with instance.remote() as r:
                    r.execute_command(cmd, run_as_root=True)
            else:
                LOG.warning(_LW('User "mapr" does not exists'))

        util.execute_on_instances(instances, set_user_password)
        util.execute_on_instances(instances, create_home_mapr)

    @el.provision_step(_("Execute configure.sh"))
    def _configure_sh_cluster(self, cluster_context, instances):
        LOG.debug('Executing configure.sh')

        if not instances:
            instances = cluster_context.get_instances()
        script = cluster_context.configure_sh

        db_specs = dict(mysql.MySQL.METRICS_SPECS._asdict())
        db_specs.update({
            'host': mysql.MySQL.get_db_instance(cluster_context).internal_ip,
            'port': mysql.MySQL.MYSQL_SERVER_PORT,
        })

        with context.ThreadGroup() as tg:
            for instance in instances:
                tg.spawn('configure-sh-%s' % instance.id,
                         self._configure_sh_instance, cluster_context,
                         instance, script, db_specs)
        LOG.debug('Executing configure.sh successfully completed')

    @el.provision_event(instance_reference=2)
    def _configure_sh_instance(self, cluster_context, instance, command,
                               specs):
        if not self.mapr_user_exists(instance):
            command += ' --create-user'
        if cluster_context.check_for_process(instance, mng.METRICS):
            command += (' -d %(host)s:%(port)s -du %(user)s -dp %(password)s '
                        '-ds %(db_name)s') % specs
        with instance.remote() as r:
            r.execute_command('sudo -i ' + command,
                              timeout=_CONFIGURE_SH_TIMEOUT)

    @el.provision_step(_("Configure SSH connection"))
    def _configure_ssh_connection(self, cluster_context, instances):
        @el.provision_event()
        def configure_ssh(instance):
            echo_param = 'echo "KeepAlive yes" >> ~/.ssh/config'
            echo_timeout = 'echo "ServerAliveInterval 60" >> ~/.ssh/config'
            with instance.remote() as r:
                r.execute_command(echo_param)
                r.execute_command(echo_timeout)

        util.execute_on_instances(instances, configure_ssh)

    def mapr_user_exists(self, instance):
        with instance.remote() as r:
            ec, __ = r.execute_command(
                "id -u %s" %
                'mapr', run_as_root=True, raise_when_error=False)
        return ec == 0

    def post_start(self, cluster_context, instances=None):
        instances = instances or cluster_context.get_instances()
        LOG.debug('Executing service post start hooks')
        for service in cluster_context.cluster_services:
            updated = cluster_context.filter_instances(instances,
                                                       service=service)
            service.post_start(cluster_context, updated)
        LOG.info(_LI('Post start hooks successfully executed'))

    @el.provision_step(_("Set cluster mode"))
    def _set_cluster_mode(self, cluster_context, instances):
        cluster_mode = cluster_context.cluster_mode
        if not cluster_mode:
            return

        command = "maprcli cluster mapreduce set -mode %s" % cluster_mode

        @el.provision_event()
        def set_cluster_mode(instance):
            return util.execute_command([instance], command,
                                        run_as='mapr')

        util.execute_on_instances(instances, set_cluster_mode)

    @el.provision_step(_("Install MapR repositories"))
    def _install_mapr_repo(self, cluster_context, instances):
        distro_name = cluster_context.distro.name

        @el.provision_event()
        def install_mapr_repos(instance):
            return util.run_script(instance, ADD_MAPR_REPO_SCRIPT, "root",
                                   distro_name, **cluster_context.mapr_repos)

        util.execute_on_instances(instances, install_mapr_repos)

    def _update_services(self, cluster_context, instances):
        for service in cluster_context.cluster_services:
            updated = cluster_context.filter_instances(instances,
                                                       service=service)
            service.update(cluster_context, updated)

    def _restart_services(self, cluster_context):
        restart = cluster_context.should_be_restarted
        for service, instances in six.iteritems(restart):
            service.restart(util.unique_list(instances))

    def _post_configure_sh(self, cluster_context, instances):
        LOG.debug('Executing post configure.sh hooks')
        for service in cluster_context.cluster_services:
            service.post_configure_sh(cluster_context, instances)
        LOG.info(_LI('Post configure.sh hooks successfully executed'))

    def _post_configure_services(self, cluster_context, instances):
        for service in cluster_context.cluster_services:
            service.post_configure(cluster_context, instances)
