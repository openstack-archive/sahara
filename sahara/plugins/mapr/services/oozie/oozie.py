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

from oslo_log import log as logging

import sahara.context as context
import sahara.plugins.mapr.domain.configuration_file as bcf
import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.mysql.mysql as mysql
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.util.validation_utils as vu

LOG = logging.getLogger(__name__)
OOZIE_START_DELAY = 30

OOZIE = np.NodeProcess(
    name='oozie',
    ui_name='Oozie',
    package='mapr-oozie',
    open_ports=[11000]
)


class Oozie(s.Service):
    def __init__(self):
        super(Oozie, self).__init__()
        self._name = 'oozie'
        self._ui_name = 'Oozie'
        self._node_processes = [OOZIE]
        self._cluster_defaults = ['oozie-default.json']
        self._validation_rules = [vu.exactly(1, OOZIE)]
        self._ui_info = [('Oozie', OOZIE,
                          {s.SERVICE_UI: 'http://%s:11000/oozie'})]

    def libext_path(self):
        return '/opt/mapr/oozie/oozie-%s/oozie-server/lib/' % self.version

    def get_config_files(self, cluster_context, configs, instance=None):
        oozie_site = bcf.HadoopXML("oozie-site.xml")
        oozie_site.remote_path = self.conf_dir(cluster_context)
        if instance:
            oozie_site.fetch(instance)
        oozie_site.load_properties(configs)
        oozie_site.add_properties(self._get_oozie_site_props(cluster_context))
        return [oozie_site]

    def _get_oozie_site_props(self, cluster_context):
        oozie_specs = mysql.MySQL.OOZIE_SPECS

        return {
            'oozie.db.schema.name': oozie_specs.db_name,
            'oozie.service.JPAService.create.db.schema': True,
            'oozie.service.JPAService.jdbc.driver': mysql.MySQL.DRIVER_CLASS,
            'oozie.service.JPAService.jdbc.url': self._get_jdbc_uri(
                cluster_context),
            'oozie.service.JPAService.jdbc.username': oozie_specs.user,
            'oozie.service.JPAService.jdbc.password': oozie_specs.password,
            'oozie.service.HadoopAccessorService.hadoop.configurations':
                '*=%s' % cluster_context.hadoop_conf
        }

    def _get_jdbc_uri(self, cluster_context):
        jdbc_uri = ('jdbc:mysql://%(db_host)s:%(db_port)s/%(db_name)s?'
                    'createDatabaseIfNotExist=true')
        jdbc_args = {
            'db_host': mysql.MySQL.get_db_instance(
                cluster_context).internal_ip,
            'db_port': mysql.MySQL.MYSQL_SERVER_PORT,
            'db_name': mysql.MySQL.OOZIE_SPECS.db_name,
        }
        return jdbc_uri % jdbc_args

    def install(self, cluster_context, instances):
        # oozie requires executed configure.sh
        pass

    def post_configure(self, cluster_context, instances):
        super(Oozie, self).install(cluster_context, instances)
        oozie_instances = cluster_context.filter_instances(instances,
                                                           service=self)
        for instance in oozie_instances:
            with instance.remote() as r:
                r.execute_command(
                    'sudo cp '
                    '/opt/mapr/oozie/oozie-%s/conf/warden.oozie.conf '
                    '/opt/mapr/conf/conf.d' % self.version)

    def post_install(self, cluster_context, instances):
        oozie_inst = cluster_context.get_instance(OOZIE)
        oozie_service = cluster_context.get_service(OOZIE)

        if oozie_service:
            symlink_cmd = (
                'cp /usr/share/java/mysql-connector-java.jar %s' %
                self.libext_path())
            with oozie_inst.remote() as r:
                LOG.debug('Installing MySQL connector for Oozie')
                r.execute_command(symlink_cmd, run_as_root=True,
                                  raise_when_error=False)
        self._set_service_dir_owner(cluster_context, instances)

    def post_start(self, cluster_context, instances):
        instances = cluster_context.filter_instances(instances, OOZIE)
        self._rebuild(cluster_context, instances)

    @g.remote_command(1)
    def _rebuild_oozie_war(self, remote, cluster_context):
        cmd = '%(home)s/bin/oozie-setup.sh -hadoop %(version)s' \
              ' /opt/mapr/hadoop/hadoop-%(version)s'
        args = {'home': self.home_dir(cluster_context),
                'version': cluster_context.hadoop_version}
        remote.execute_command(cmd % args, run_as_root=True)

    def update(self, cluster_context, instances=None):
        instances = instances or cluster_context.get_instances()
        instances = cluster_context.filter_instances(instances, OOZIE)
        self._rebuild(cluster_context, instances)

    def _rebuild(self, cluster_context, instances):
        OOZIE.stop(filter(OOZIE.is_started, instances))
        g.execute_on_instances(
            instances, self._rebuild_oozie_war, cluster_context)
        OOZIE.start(instances)
        context.sleep(OOZIE_START_DELAY)


class OozieV401(Oozie):
    def __init__(self):
        super(OozieV401, self).__init__()
        self._version = '4.0.1'
        self._dependencies = [('mapr-oozie-internal', self.version)]


class OozieV410(Oozie):
    def __init__(self):
        super(OozieV410, self).__init__()
        self._version = '4.1.0'
        self._dependencies = [('mapr-oozie-internal', self.version)]


class OozieV420(Oozie):
    def __init__(self):
        super(OozieV420, self).__init__()
        self._version = '4.2.0'
        self._dependencies = [('mapr-oozie-internal', self.version)]

    def libext_path(self):
        return '/opt/mapr/oozie/oozie-%s/libext/' % self.version

    def post_install(self, cluster_context, instances):
        super(OozieV420, self).post_install(cluster_context, instances)
        self.fix_oozie_bug(cluster_context)

    def fix_oozie_bug(self, cluster_context):
        """Wrong maprfs jar bug

        On some environments Oozie installation
        process takes incorrect jar that causes failure
        to run jobs. This is a temporary bug in Oozie and
        is going to be fixed soon.
        """

        if cluster_context.mapr_version != '5.1.0':
            return
        oozie_inst = cluster_context.get_instance(OOZIE)
        command = "sudo rm /opt/mapr/hadoop/hadoop-2.7.0/share/hadoop/kms/" \
                  "tomcat/webapps/kms/WEB-INF/lib/maprfs-5.1.0-mapr.jar" \
                  " && sudo ln -s /opt/mapr/lib/maprfs-5.1.0-mapr.jar" \
                  " /opt/mapr/hadoop/hadoop-2.7.0/share/hadoop/kms/" \
                  "tomcat/webapps/kms/WEB-INF/lib/maprfs-5.1.0-mapr.jar"
        with oozie_inst.remote() as r:
            r.execute_command(command, run_as_root=True)
