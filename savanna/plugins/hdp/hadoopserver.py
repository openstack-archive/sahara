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
from savanna.utils import remote
import six

LOG = logging.getLogger(__name__)


class HadoopServer:
    _master_ip = None

    def __init__(self, instance, node_group):
        self.instance = instance
        self.node_group = node_group
        self._ssh = self._connect_to_vm()

    def _connect_to_vm(self):
        LOG.info(
            'Connecting to VM: {0}'.format(self.instance.management_ip))
        return self.instance.remote.ssh_connection()

    def provision_ambari(self, ambari_server_ip):
        self.install_rpms()
        if 'AMBARI_SERVER' in self.node_group.components:
            self._setup_and_start_ambari_server()

        if 'AMBARI_AGENT' in self.node_group.components:
            self._setup_and_start_ambari_agent(ambari_server_ip)

    def install_rpms(self):
        LOG.info(
            "{0}: Installing rpm's ...".format(self.instance.hostname))

        #TODO(jspeidel): based on image type, use correct command
        rpm_cmd = 'rpm -Uvh http://s3.amazonaws.com/dev.hortonworks' \
                  '.com/AMBARI.b6-1.x/repos/centos6/AMBARI.b6-1.x-1.el6' \
                  '.noarch.rpm'
        self._execute_on_vm(rpm_cmd)
        self._execute_on_vm('yum -y install epel-release')

    def _setup_and_start_ambari_server(self):
        LOG.info(
            '{0}: Installing ambari-server ...'.format(self.instance.hostname))
        self._execute_on_vm('yum -y install ambari-server')

        LOG.info('Running Ambari Server setup ...')
        self._execute_on_vm_interactive('ambari-server setup',
                                        DefaultPromptMatcher(
                                            "Ambari Server 'setup' finished "
                                            "successfully",
                                            LOG))

        LOG.info('Starting Ambari ...')
        self._execute_on_vm('ambari-server start')

    def _setup_and_start_ambari_agent(self, ambari_server_ip):
        LOG.info(
            '{0}: Installing Ambari Agent ...'.format(self.instance.hostname))

        self._execute_on_vm('yum -y install ambari-agent')
        LOG.debug(
            '{0}: setting master-ip: {1} in ambari-agent.ini'.format(
                self.instance.hostname, ambari_server_ip))
        self._replace_str_in_remote_file(
            '/etc/ambari-agent/conf/ambari-agent.ini', 'localhost',
            ambari_server_ip)

        LOG.info(
            '{0}: Starting Ambari Agent ...'.format(self.instance.hostname))
        self._execute_on_vm('ambari-agent start')

    def _configure_ganglia(self, ganglia_server_ip):
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
            self._replace_str_in_remote_file(
                '/etc/ganglia/hdp/HDPSlaves/conf.d/gmond.slave.conf',
                'host = {0}'.format(self.instance.hostname),
                'host = {0}'.format(ganglia_server_ip))
            self._replace_str_in_remote_file(
                '/etc/ganglia/hdp/HDPJobTracker/conf.d/gmond.slave.conf',
                'host = {0}'.format(self.instance.hostname),
                'host = {0}'.format(ganglia_server_ip))
            self._replace_str_in_remote_file(
                '/etc/ganglia/hdp/HDPNameNode/conf.d/gmond.slave.conf',
                'host = {0}'.format(self.instance.hostname),
                'host = {0}'.format(ganglia_server_ip))
            self._replace_str_in_remote_file(
                '/etc/ganglia/hdp/HDPHBaseMaster/conf.d/gmond.slave.conf',
                'host = {0}'.format(self.instance.hostname),
                'host = {0}'.format(ganglia_server_ip))

        #master config
        if self._is_ganglia_master():
            self._replace_str_in_remote_file(
                '/etc/ganglia/hdp/HDPSlaves/conf.d/gmond.master.conf',
                'bind = {0}'.format(self.instance.hostname), '')
            self._replace_str_in_remote_file(
                '/etc/ganglia/hdp/HDPJobTracker/conf.d/gmond.master.conf',
                'bind = {0}'.format(self.instance.hostname), '')
            self._replace_str_in_remote_file(
                '/etc/ganglia/hdp/HDPNameNode/conf.d/gmond.master.conf',
                'bind = {0}'.format(self.instance.hostname), '')
            #TODO(jspeidel): appears only to be necessary if hbase is installed
        #            self._replace_str_in_remote_file(self._ssh,
        # '/etc/ganglia/hdp/HDPHBaseMaster/conf.d/gmond.master.conf',
        #                                             'bind = {0}'.format(
        # self.instance.fqdn), '')

        # gangliaClusters.conf
        self._replace_str_in_remote_file(
            '/usr/libexec/hdp/ganglia/gangliaClusters.conf',
            self.instance.fqdn, ganglia_server_ip)

        # update puppet templates and shell scripts because they generate
        # configs that are used after restart
        # gangliaClusters.conf template
        #TODO(jspeidel): modify file where prop "ganglia_server_host" is set
        self._replace_str_in_remote_file(
            '/var/lib/ambari-agent/puppet/modules/hdp-ganglia/templates'
            '/gangliaClusters.conf.erb',
            '<%=scope.function_hdp_host("ganglia_server_host")%>',
            ganglia_server_ip)

        # gmondLib.sh This script generates the master and slave configs
        #TODO(jspeidel): combine into one call.  Pass map of old/new values
        self._replace_str_in_remote_file(
            '/var/lib/ambari-agent/puppet/modules/hdp-ganglia/files/gmondLib'
            '.sh',
            'bind = ${gmondMasterIP}', '')
        self._replace_str_in_remote_file(
            '/var/lib/ambari-agent/puppet/modules/hdp-ganglia/files/gmondLib'
            '.sh',
            'host = ${gmondMasterIP}', 'host = {0}'.format(ganglia_server_ip))
        self._replace_str_in_remote_file(
            '/usr/libexec/hdp/ganglia/gmondLib.sh',
            'bind = ${gmondMasterIP}', '')
        self._replace_str_in_remote_file(
            '/usr/libexec/hdp/ganglia/gmondLib.sh',
            'host = ${gmondMasterIP}', 'host = {0}'.format(ganglia_server_ip))

    def update_hosts_file(self, hosts):
        # read the hosts file
        data = remote.read_file_from(self._ssh.open_sftp(), '/etc/hosts')
        output = six.StringIO()
        for host in hosts:
            output.write('{0}   {1}\n'.format(host.instance.internal_ip,
                                              host.instance.fqdn))
        output.write('\n')

        # add the previous file contents
        output.write(data)

        # write the file back
        LOG.debug("updating hosts file with the following:")
        LOG.debug(output.getvalue())
        remote.write_file_to(self._ssh.open_sftp(), '/etc/hosts',
                             output.getvalue())

    def _replace_str_in_remote_file(self, filename, origStr, newStr):
        s = ''

        client = self._ssh.open_sftp()
        #check that file exists
        try:
            client.stat(filename)
            client.close()
        except IOError:
            LOG.debug(
                "File to edit doesn't exist: {0}".format(filename))
            return

        # copy the file locally
        data = remote.read_file_from(self._ssh.open_sftp(), filename)
        # read thru lines and replace origStr with newStr
        for line in six.StringIO(data):
            if origStr in line:
                if newStr != '':
                    s += line.replace(origStr, newStr)
            else:
                s += line

        # write the file back out
        remote.write_file_to(self._ssh.open_sftp(), filename, s)

    def _log(self, buf):
        LOG.debug(buf)

    def _execute_on_vm_interactive(self, cmd, matcher):
        LOG.debug(
            "{0}: Executing interactive remote command '{1}'".format(
                self.instance.hostname, cmd))

        buf = ''
        all_output = ''
        channel = self._ssh.invoke_shell()
        try:
            channel.send(cmd + '\n')
            while not matcher.is_eof(buf):
                buf += channel.recv(4096)
                response = matcher.get_response(buf)
                if response is not None:
                    channel.send(response + '\n')
                    all_output += buf
                    buf = ''
        finally:
            channel.close()
            self._log(all_output)
            self._log(buf)

    def _execute_on_vm(self, cmd):
        LOG.debug("{0}: Executing remote command '{1}'".format(
            self.instance.hostname, cmd))
        LOG.debug(
            'Executing using instance: id = {0}, hostname = {1}'.format(
                self.instance.instance_id,
                self.instance.hostname))
        remote.execute_command(self._ssh, cmd)

    def _is_component_available(self, component):
        return component in self.node_group.components

    def _is_ganglia_master(self):
        return self._is_component_available('GANGLIA_SERVER')

    def _is_ganglia_slave(self):
        return self._is_component_available('GANGLIA_MONITOR')


class DefaultPromptMatcher():
    prompt_pattern = re.compile('(.*\()(.)(\)\?\s*$)', re.DOTALL)

    def __init__(self, terminal_token, logger):
        self.eof_token = terminal_token
        self.logger = logger

    def get_response(self, s):
        match = self.prompt_pattern.match(s)
        if match:
            response = match.group(2)
            LOG.debug(
                "Returning response '{0}' for prompt '{1}'".format(
                    response, s.rstrip().rsplit('\n', 1)[-1]))
            return response
        else:
            return None

    def is_eof(self, s):
        eof = self.eof_token in s
        if eof:
            LOG.debug('Returning eof = True')
        return eof
