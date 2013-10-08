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

from savanna.openstack.common import log as logging
from savanna.plugins.hdp import savannautils


AMBARI_RPM = 'http://s3.amazonaws.com/public-repo-1.hortonworks.com/' \
             'ambari/centos6/1.x/updates/1.2.5.17/ambari.repo'

HADOOP_SWIFT_RPM = 'https://s3.amazonaws.com/public-repo-1.hortonworks.com/' \
                   'savanna/swift/hadoop-swift-1.0-1.x86_64.rpm'

LOG = logging.getLogger(__name__)


class HadoopServer:
    _master_ip = None

    def __init__(self, instance, node_group, ambari_rpm=None):
        self.instance = instance
        self.node_group = node_group
        self.ambari_rpm = ambari_rpm or AMBARI_RPM

    def provision_ambari(self, ambari_info):
        self.install_rpms()
        if 'AMBARI_SERVER' in self.node_group.components:
            self._setup_and_start_ambari_server(ambari_info.port)

        if 'AMBARI_AGENT' in self.node_group.components:
            self._setup_and_start_ambari_agent(ambari_info.host.internal_ip)

    @savannautils.inject_remote('r')
    def install_rpms(self, r):
        LOG.info(
            "{0}: Installing rpm's ...".format(self.instance.hostname))

        #TODO(jspeidel): based on image type, use correct command
        rpm_cmd = 'curl -s -o /etc/yum.repos.d/ambari.repo %s' % \
                  self.ambari_rpm
        r.execute_command(rpm_cmd)
        r.execute_command('yum -y install epel-release')

    @savannautils.inject_remote('r')
    def install_swift_integration(self, r):
        LOG.info(
            "{0}: Installing swift integration ..."
            .format(self.instance.hostname))

        rpm_cmd = 'rpm -Uvh ' + HADOOP_SWIFT_RPM
        r.execute_command(rpm_cmd)

    @savannautils.inject_remote('r')
    def _setup_and_start_ambari_server(self, port, r):
        LOG.info(
            '{0}: Installing ambari-server ...'.format(self.instance.hostname))
        r.execute_command('yum -y install ambari-server')

        LOG.info('Running Ambari Server setup ...')
        r.execute_on_vm_interactive(
            'ambari-server setup', DefaultPromptMatcher(
                "Ambari Server 'setup' completed successfully"))

        self._configure_ambari_server_api_port(port)

        LOG.info('Starting Ambari ...')
        # NOTE(dmitryme): Reading stdout from 'ambari-server start'
        # hangs ssh. Redirecting output to /dev/null fixes that
        r.execute_command('ambari-server start > /dev/null 2>&1')

    @savannautils.inject_remote('r')
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
        r.write_file_to(ambari_config_file, data)

    @savannautils.inject_remote('r')
    def _setup_and_start_ambari_agent(self, ambari_server_ip, r):
        LOG.info(
            '{0}: Installing Ambari Agent ...'.format(self.instance.hostname))

        r.execute_command('yum -y install ambari-agent')
        LOG.debug(
            '{0}: setting master-ip: {1} in ambari-agent.ini'.format(
                self.instance.hostname, ambari_server_ip))
        r.replace_remote_string(
            '/etc/ambari-agent/conf/ambari-agent.ini', 'localhost',
            ambari_server_ip)

        LOG.info(
            '{0}: Starting Ambari Agent ...'.format(self.instance.hostname))
        r.execute_command('ambari-agent start')

    @savannautils.inject_remote('r')
    def _configure_ganglia(self, ganglia_server_ip, r):
        #TODO(John): the set of files to update is now dependent on which
        # components are deployed on a host
        #TODO(jspeidel): so we these calls should be based on configuration
        LOG.debug(
            '{0}: Updating Ganglia host configuration ...'.format(
                self.instance.hostname))

        # slave config
        #TODO(jspeidel): set MASTER_SLAVE for master where only one node is
        # deployed
        if self._is_ganglia_slave() or self._is_ganglia_master():
            r.replace_remote_string(
                '/etc/ganglia/hdp/HDPSlaves/conf.d/gmond.slave.conf',
                'host = {0}'.format(self.instance.hostname),
                'host = {0}'.format(ganglia_server_ip))
            r.replace_remote_string(
                '/etc/ganglia/hdp/HDPJobTracker/conf.d/gmond.slave.conf',
                'host = {0}'.format(self.instance.hostname),
                'host = {0}'.format(ganglia_server_ip))
            r.replace_remote_string(
                '/etc/ganglia/hdp/HDPNameNode/conf.d/gmond.slave.conf',
                'host = {0}'.format(self.instance.hostname),
                'host = {0}'.format(ganglia_server_ip))
            r.replace_remote_string(
                '/etc/ganglia/hdp/HDPHBaseMaster/conf.d/gmond.slave.conf',
                'host = {0}'.format(self.instance.hostname),
                'host = {0}'.format(ganglia_server_ip))

        #master config
        if self._is_ganglia_master():
            r.replace_remote_string(
                '/etc/ganglia/hdp/HDPSlaves/conf.d/gmond.master.conf',
                'bind = {0}'.format(self.instance.hostname), '')
            r.replace_remote_string(
                '/etc/ganglia/hdp/HDPJobTracker/conf.d/gmond.master.conf',
                'bind = {0}'.format(self.instance.hostname), '')
            r.replace_remote_string(
                '/etc/ganglia/hdp/HDPNameNode/conf.d/gmond.master.conf',
                'bind = {0}'.format(self.instance.hostname), '')
            #TODO(jspeidel): appears only to be necessary if hbase is installed
        #            r.replace_remote_string(
        # '/etc/ganglia/hdp/HDPHBaseMaster/conf.d/gmond.master.conf',
        #                                             'bind = {0}'.format(
        # self.instance.fqdn), '')

        # gangliaClusters.conf
        r.replace_remote_string(
            '/usr/libexec/hdp/ganglia/gangliaClusters.conf',
            self.instance.fqdn, ganglia_server_ip)

        # update puppet templates and shell scripts because they generate
        # configs that are used after restart
        # gangliaClusters.conf template
        #TODO(jspeidel): modify file where prop "ganglia_server_host" is set
        r.replace_remote_string(
            '/var/lib/ambari-agent/puppet/modules/hdp-ganglia/templates'
            '/gangliaClusters.conf.erb',
            '<%=scope.function_hdp_host("ganglia_server_host")%>',
            ganglia_server_ip)

        # gmondLib.sh This script generates the master and slave configs
        #TODO(jspeidel): combine into one call.  Pass map of old/new values
        r.replace_remote_string(
            '/var/lib/ambari-agent/puppet/modules/hdp-ganglia/files/gmondLib'
            '.sh',
            'bind = ${gmondMasterIP}', '')
        r.replace_remote_string(
            '/var/lib/ambari-agent/puppet/modules/hdp-ganglia/files/gmondLib'
            '.sh',
            'host = ${gmondMasterIP}', 'host = {0}'.format(ganglia_server_ip))
        r.replace_remote_string(
            '/usr/libexec/hdp/ganglia/gmondLib.sh',
            'bind = ${gmondMasterIP}', '')
        r.replace_remote_string(
            '/usr/libexec/hdp/ganglia/gmondLib.sh',
            'host = ${gmondMasterIP}', 'host = {0}'.format(ganglia_server_ip))

    def _log(self, buf):
        LOG.debug(buf)

    def _is_component_available(self, component):
        return component in self.node_group.components

    def _is_ganglia_master(self):
        return self._is_component_available('GANGLIA_SERVER')

    def _is_ganglia_slave(self):
        return self._is_component_available('GANGLIA_MONITOR')


class DefaultPromptMatcher():
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
