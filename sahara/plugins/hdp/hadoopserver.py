# Copyright (c) 2013 Hortonworks, Inc.
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

import re

from oslo_log import log as logging

from sahara.i18n import _
from sahara.i18n import _LI
from sahara.plugins import exceptions as ex
from sahara.plugins.hdp import saharautils
from sahara.utils import files as f


AMBARI_RPM = ('http://s3.amazonaws.com/public-repo-1.hortonworks.com/'
              'ambari/centos6/1.x/updates/1.6.0/ambari.repo')

EPEL_RELEASE_PACKAGE_NAME = 'epel-release'

HADOOP_SWIFT_RPM = ('https://s3.amazonaws.com/public-repo-1.hortonworks.com/'
                    'sahara/swift/hadoop-swift-1.0-1.x86_64.rpm')

HADOOP_SWIFT_LOCAL_RPM = ('/opt/hdp-local-repos/hadoop-swift/'
                          'hadoop-swift-1.0-1.x86_64.rpm')

LOG = logging.getLogger(__name__)


class HadoopServer(object):
    _master_ip = None

    def __init__(self, instance, node_group, ambari_rpm=None):
        self.instance = instance
        self.node_group = node_group
        self.ambari_rpm = ambari_rpm or AMBARI_RPM

    def provision_ambari(self, ambari_info, cluster_spec):
        self.install_rpms()
        global_config = cluster_spec.configurations['global']
        jdk_path = global_config.get('java64_home')
        if 'AMBARI_SERVER' in self.node_group.components:
            self._setup_and_start_ambari_server(ambari_info.port, jdk_path)

        # all nodes must run Ambari agent
        self._setup_and_start_ambari_agent(ambari_info.host.internal_ip)

    @saharautils.inject_remote('r')
    def rpms_installed(self, r):
        rpm_cmd = 'rpm -q %s' % EPEL_RELEASE_PACKAGE_NAME
        ret_code, stdout = r.execute_command(rpm_cmd,
                                             run_as_root=True,
                                             raise_when_error=False)
        return ret_code == 0

    @saharautils.inject_remote('r')
    def install_rpms(self, r):
        LOG.info(
            _LI("{0}: Installing rpm's ...").format(self.instance.hostname()))

        # TODO(jspeidel): based on image type, use correct command
        curl_cmd = ('curl -f -s -o /etc/yum.repos.d/ambari.repo %s' %
                    self.ambari_rpm)
        ret_code, stdout = r.execute_command(curl_cmd,
                                             run_as_root=True,
                                             raise_when_error=False)
        if ret_code == 0:
            yum_cmd = 'yum -y install %s' % EPEL_RELEASE_PACKAGE_NAME
            r.execute_command(yum_cmd, run_as_root=True)
        else:
            LOG.info(_LI("{0}: Unable to install rpm's from repo, "
                         "checking for local install.")
                     .format(self.instance.hostname()))
            if not self.rpms_installed():
                raise ex.HadoopProvisionError(
                    _('Failed to install Hortonworks Ambari'))

    @saharautils.inject_remote('r')
    def install_swift_integration(self, r):
        LOG.info(
            _LI("{0}: Installing swift integration ...")
            .format(self.instance.hostname()))
        base_rpm_cmd = 'rpm -U --quiet '
        rpm_cmd = base_rpm_cmd + HADOOP_SWIFT_RPM
        ret_code, stdout = r.execute_command(rpm_cmd,
                                             run_as_root=True,
                                             raise_when_error=False)
        if ret_code != 0:
            LOG.info(_LI("{0}: Unable to install swift integration from "
                         "source, checking for local rpm.")
                     .format(self.instance.hostname()))
            ret_code, stdout = r.execute_command(
                'ls ' + HADOOP_SWIFT_LOCAL_RPM,
                run_as_root=True,
                raise_when_error=False)
            if ret_code == 0:
                rpm_cmd = base_rpm_cmd + HADOOP_SWIFT_LOCAL_RPM
                r.execute_command(rpm_cmd, run_as_root=True)
            else:
                raise ex.HadoopProvisionError(
                    _('Failed to install Hadoop Swift integration'))

    @saharautils.inject_remote('r')
    def configure_topology(self, topology_str, r):
        r.write_file_to(
            '/etc/hadoop/conf/topology.sh',
            f.get_file_text(
                'plugins/hdp/versions/version_1_3_2/resources/topology.sh'))
        r.execute_command(
            'chmod +x /etc/hadoop/conf/topology.sh', run_as_root=True
        )
        r.write_file_to('/etc/hadoop/conf/topology.data', topology_str)

    @saharautils.inject_remote('r')
    def _setup_and_start_ambari_server(self, port, jdk_path, r):
        LOG.info(_LI('{0}: Installing ambari-server ...').format(
            self.instance.hostname()))
        r.execute_command('yum -y install ambari-server', run_as_root=True)

        LOG.info(_LI('Running Ambari Server setup ...'))
        # remove postgres data directory as a precaution since its existence
        # has prevented successful postgres installation
        r.execute_command('rm -rf /var/lib/pgsql/data', run_as_root=True)

        # determine if the JDK is installed on this image
        # in the case of the plain image, no JDK will be available
        return_code, stdout = r.execute_command('ls -l {jdk_location}'.format(
            jdk_location=jdk_path), raise_when_error=False)

        LOG.debug('Queried for JDK location on VM instance, return code = ' +
                  str(return_code))

        # do silent setup since we only use default responses now
        # only add -j command if the JDK is configured for the template,
        # and if the JDK is present
        # in all other cases, allow Ambari to install the JDK
        r.execute_command(
            'ambari-server setup -s {jdk_arg} > /dev/null 2>&1'.format(
                jdk_arg='-j ' + jdk_path if jdk_path and (return_code == 0)
                else ''),
            run_as_root=True, timeout=1800
        )

        self._configure_ambari_server_api_port(port)

        LOG.info(_LI('Starting Ambari ...'))
        # NOTE(dmitryme): Reading stdout from 'ambari-server start'
        # hangs ssh. Redirecting output to /dev/null fixes that
        r.execute_command(
            'ambari-server start > /dev/null 2>&1', run_as_root=True
        )

    @saharautils.inject_remote('r')
    def _configure_ambari_server_api_port(self, port, r):
        # do nothing if port is not specified or is default
        if port is None or port == 8080:
            return

        ambari_config_file = '/etc/ambari-server/conf/ambari.properties'
        LOG.debug('Configuring Ambari Server API port: {0}'.format(port))
        # read the current contents
        data = r.read_file_from(ambari_config_file)
        data = '{0}\nclient.api.port={1}\n'.format(data, port)

        # write the file back
        r.write_file_to(ambari_config_file, data, run_as_root=True)

    @saharautils.inject_remote('r')
    def _setup_and_start_ambari_agent(self, ambari_server_ip, r):
        LOG.info(_LI('{0}: Installing Ambari Agent ...').format(
            self.instance.hostname()))

        r.execute_command('yum -y install ambari-agent', run_as_root=True)
        LOG.debug(
            '{0}: setting master-ip: {1} in ambari-agent.ini'.format(
                self.instance.hostname(), ambari_server_ip))
        r.replace_remote_string(
            '/etc/ambari-agent/conf/ambari-agent.ini', 'localhost',
            ambari_server_ip)

        LOG.info(
            _LI('{0}: Starting Ambari Agent ...').format(
                self.instance.hostname()))
        # If the HDP 2 ambari agent is pre-installed on an image, the agent
        # will start up during instance launch and therefore the agent
        # registration will fail.  It is therefore more appropriate to call
        # restart since it will either start (if stopped) or restart (if
        # running)
        r.execute_command('ambari-agent restart', run_as_root=True)

    @saharautils.inject_remote('r')
    def set_namenode_safemode(self, jh, r):
        r.execute_command("sudo su -l hdfs -c 'JAVA_HOME={0} "
                          "hdfs dfsadmin -safemode enter'".format(jh),
                          run_as_root=True)

    @saharautils.inject_remote('r')
    def save_namenode_namespace(self, jh, r):
        r.execute_command("sudo su -l hdfs -c 'JAVA_HOME={0} "
                          "hdfs dfsadmin -saveNamespace'".format(jh),
                          run_as_root=True)

    @saharautils.inject_remote('r')
    def initialize_shared_edits(self, jh, r):
        r.execute_command("sudo su -l hdfs -c 'JAVA_HOME={0} "
                          "hdfs namenode -initializeSharedEdits'".format(jh),
                          run_as_root=True)

    @saharautils.inject_remote('r')
    def format_zookeeper_fc(self, jh, r):
        r.execute_command("sudo su -l hdfs -c 'JAVA_HOME={0} "
                          "hdfs zkfc -formatZK'".format(jh),
                          run_as_root=True)

    @saharautils.inject_remote('r')
    def bootstrap_standby_namenode(self, jh, r):
        r.execute_command("sudo su -l hdfs -c 'JAVA_HOME={0} "
                          "hdfs namenode -bootstrapStandby'".format(jh),
                          run_as_root=True)

    @saharautils.inject_remote('r')
    def install_httpfs(self, r):
        r.execute_command("yum -y install hadoop-httpfs", run_as_root=True)

    @saharautils.inject_remote('r')
    def start_httpfs(self, r):
        r.execute_command("service hadoop-httpfs start", run_as_root=True)

    @saharautils.inject_remote('r')
    def write_hue_temp_file(self, filename, content, r):
        r.execute_command("echo %s > %s" % (content, filename),
                          run_as_root=True)

    def _log(self, buf):
        LOG.debug(buf)

    def _is_component_available(self, component):
        return component in self.node_group.components

    def _is_ganglia_master(self):
        return self._is_component_available('GANGLIA_SERVER')

    def _is_ganglia_slave(self):
        return self._is_component_available('GANGLIA_MONITOR')


class DefaultPromptMatcher(object):
    prompt_pattern = re.compile('(.*\()(.)(\)\?\s*$)', re.DOTALL)

    def __init__(self, terminal_token):
        self.eof_token = terminal_token

    def get_response(self, s):
        match = self.prompt_pattern.match(s)
        if match:
            response = match.group(2)
            return response
        else:
            return None

    def is_eof(self, s):
        eof = self.eof_token in s
        return eof
