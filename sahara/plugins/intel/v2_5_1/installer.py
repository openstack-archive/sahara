# Copyright (c) 2013 Intel Corporation
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

import telnetlib

import six

from sahara import conductor
from sahara import context
from sahara.openstack.common import log as logging
from sahara.plugins.general import utils as u
from sahara.plugins.intel import exceptions as iex
from sahara.plugins.intel.v2_5_1 import client as c
from sahara.plugins.intel.v2_5_1 import config_helper as c_helper
from sahara.swift import swift_helper as swift
from sahara.utils import crypto


conductor = conductor.API
LOG = logging.getLogger(__name__)

_INST_CONF_TEMPLATE = """
network_interface=eth0
mode=silent
accept_jdk_license=accept
how_to_setup_os_repo=2
os_repo=%s
os_repo_username=
os_repo_password=
os_repo_proxy=
how_to_setup_idh_repo=1
idh_repo=%s
idh_repo_username=
idh_repo_password=
idh_repo_proxy=
firewall_selinux_setting=1"""


def install_manager(cluster):
    LOG.info("Starting Install Manager Process")
    mng_instance = u.get_instance(cluster, 'manager')

    idh_tarball_path = c_helper.get_config_value(
        cluster.cluster_configs.get('general'), c_helper.IDH_TARBALL_URL)

    idh_tarball_filename = idh_tarball_path.rsplit('/', 1)[-1]
    idh_dir = idh_tarball_filename[:idh_tarball_filename.find('.tar.gz')]
    LOG.info("IDH tgz will be retrieved from: \'%s\'", idh_tarball_path)

    idh_repo = c_helper.get_config_value(
        cluster.cluster_configs.get('general'), c_helper.IDH_REPO_URL)

    os_repo = c_helper.get_config_value(
        cluster.cluster_configs.get('general'), c_helper.OS_REPO_URL)

    idh_install_cmd = 'sudo ./%s/install.sh --mode=silent 2>&1' % idh_dir

    with mng_instance.remote() as r:
        LOG.info("Download IDH manager ")
        try:
            r.execute_command('curl -O %s 2>&1' % idh_tarball_path)
        except Exception as e:
            raise RuntimeError("Unable to download IDH manager from %s" %
                               idh_tarball_path, e)

        # unpack archive
        LOG.info("Unpack manager %s ", idh_tarball_filename)
        try:
            r.execute_command('tar xzf %s 2>&1' % idh_tarball_filename)
        except Exception as e:
            raise RuntimeError("Unable to unpack tgz %s",
                               idh_tarball_filename, e)

        # install idh
        LOG.debug("Install manager with %s : ", idh_install_cmd)
        inst_conf = _INST_CONF_TEMPLATE % (os_repo, idh_repo)
        r.write_file_to('%s/ui-installer/conf' % idh_dir, inst_conf)
        #TODO(alazarev) make timeout configurable (bug #1262897)
        r.execute_command(idh_install_cmd, timeout=3600)

        # fix nginx persimmions bug
        r.execute_command('sudo chmod o+x /var/lib/nginx/ /var/lib/nginx/tmp '
                          '/var/lib/nginx/tmp/client_body')

    # waiting start idh manager
    #TODO(alazarev) make timeout configurable (bug #1262897)
    timeout = 600
    LOG.debug("Waiting %s seconds for Manager to start : ", timeout)
    while timeout:
        try:
            telnetlib.Telnet(mng_instance.management_ip, 9443)
            break
        except IOError:
            timeout -= 2
            context.sleep(2)
    else:
        message = ("IDH Manager failed to start in %s minutes on node '%s' "
                   "of cluster '%s'"
                   % (timeout / 60, mng_instance.management_ip, cluster.name))
        LOG.error(message)
        raise iex.IntelPluginException(message)


def configure_os(cluster):
    instances = u.get_instances(cluster)
    configure_os_from_instances(cluster, instances)


def create_hadoop_ssh_keys(cluster):
    private_key, public_key = crypto.generate_key_pair()
    extra = {
        'hadoop_private_ssh_key': private_key,
        'hadoop_public_ssh_key': public_key
    }
    return conductor.cluster_update(context.ctx(), cluster, {'extra': extra})


def configure_os_from_instances(cluster, instances):
    for instance in instances:
        with instance.remote() as remote:
            LOG.debug("Configuring OS settings on %s : ", instance.hostname())

            # configure hostname, RedHat/Centos specific
            remote.replace_remote_string('/etc/sysconfig/network',
                                         'HOSTNAME=.*',
                                         'HOSTNAME=%s' % instance.fqdn())
            # disable selinux and iptables, because Intel distribution requires
            # this to be off
            remote.execute_command('sudo /usr/sbin/setenforce 0')
            remote.replace_remote_string('/etc/selinux/config',
                                         'SELINUX=.*', 'SELINUX=disabled')
            # disable iptables
            remote.execute_command('sudo /sbin/service iptables stop')
            remote.execute_command('sudo /sbin/chkconfig iptables off')

            # create 'hadoop' user
            remote.write_files_to({
                'id_rsa': cluster.extra.get('hadoop_private_ssh_key'),
                'authorized_keys': cluster.extra.get('hadoop_public_ssh_key')
            })
            remote.execute_command(
                'sudo useradd hadoop && '
                'sudo sh -c \'echo "hadoop ALL=(ALL) NOPASSWD:ALL" '
                '>> /etc/sudoers\' && '
                'sudo mkdir -p /home/hadoop/.ssh/ && '
                'sudo mv id_rsa authorized_keys /home/hadoop/.ssh && '
                'sudo chown -R hadoop:hadoop /home/hadoop/.ssh && '
                'sudo chmod 600 /home/hadoop/.ssh/{id_rsa,authorized_keys}')

            swift_enable = c_helper.get_config_value(
                cluster.cluster_configs.get('general'), c_helper.ENABLE_SWIFT)
            if swift_enable:
                hadoop_swiftfs_jar_url = c_helper.get_config_value(
                    cluster.cluster_configs.get('general'),
                    c_helper.HADOOP_SWIFTFS_JAR_URL)
                swift_lib_dir = '/usr/lib/hadoop/lib'
                swift_lib_path = swift_lib_dir + '/hadoop-swift-latest.jar'
                cmd = ('sudo mkdir -p %s && sudo curl \'%s\' -o %s'
                       % (swift_lib_dir, hadoop_swiftfs_jar_url,
                          swift_lib_path))
                remote.execute_command(cmd)


def _configure_services(client, cluster):
    nn_host = u.get_namenode(cluster).fqdn()
    snn = u.get_secondarynamenodes(cluster)
    snn_host = snn[0].fqdn() if snn else None
    jt_host = u.get_jobtracker(cluster).fqdn() if u.get_jobtracker(
        cluster) else None
    dn_hosts = [dn.fqdn() for dn in u.get_datanodes(cluster)]
    tt_hosts = [tt.fqdn() for tt in u.get_tasktrackers(cluster)]

    oozie_host = u.get_oozie(cluster).fqdn() if u.get_oozie(
        cluster) else None
    hive_host = u.get_hiveserver(cluster).fqdn() if u.get_hiveserver(
        cluster) else None

    services = []
    if u.get_namenode(cluster):
        services += ['hdfs']

    if u.get_jobtracker(cluster):
        services += ['mapred']

    if oozie_host:
        services += ['oozie']
        services += ['pig']

    if hive_host:
        services += ['hive']

    LOG.debug("Add services: %s" % ', '.join(services))
    client.services.add(services)

    LOG.debug("Assign roles to hosts")
    client.services.hdfs.add_nodes('PrimaryNameNode', [nn_host])

    client.services.hdfs.add_nodes('DataNode', dn_hosts)
    if snn:
        client.services.hdfs.add_nodes('SecondaryNameNode', [snn_host])

    if oozie_host:
        client.services.oozie.add_nodes('Oozie', [oozie_host])

    if hive_host:
        client.services.hive.add_nodes('HiveServer', [hive_host])

    if jt_host:
        client.services.mapred.add_nodes('JobTracker', [jt_host])
        client.services.mapred.add_nodes('TaskTracker', tt_hosts)


def _configure_storage(client, cluster):
    datanode_ng = u.get_node_groups(cluster, 'datanode')[0]
    storage_paths = datanode_ng.storage_paths()
    dn_hosts = [i.fqdn() for i in u.get_datanodes(cluster)]

    name_dir_param = ",".join(
        [st_path + '/dfs/name' for st_path in storage_paths])
    data_dir_param = ",".join(
        [st_path + '/dfs/data' for st_path in storage_paths])
    client.params.hdfs.update('dfs.name.dir', name_dir_param)
    client.params.hdfs.update('dfs.data.dir', data_dir_param, nodes=dn_hosts)


def _configure_swift(client, cluster):
    swift_enable = c_helper.get_config_value(
        cluster.cluster_configs.get('general'), c_helper.ENABLE_SWIFT)
    if swift_enable:
        swift_configs = swift.get_swift_configs()
        for conf in swift_configs:
            client.params.hadoop.add(conf['name'], conf['value'])


def _add_user_params(client, cluster):
    for p in six.iteritems(cluster.cluster_configs.get("Hadoop", {})):
        client.params.hadoop.update(p[0], p[1])

    for p in six.iteritems(cluster.cluster_configs.get("HDFS", {})):
        client.params.hdfs.update(p[0], p[1])

    for p in six.iteritems(cluster.cluster_configs.get("MapReduce", {})):
        client.params.mapred.update(p[0], p[1])

    for p in six.iteritems(cluster.cluster_configs.get("JobFlow", {})):
        client.params.oozie.update(p[0], p[1])


def install_cluster(cluster):
    mng_instance = u.get_instance(cluster, 'manager')

    all_hosts = list(set([i.fqdn() for i in u.get_instances(cluster)]))

    client = c.IntelClient(mng_instance, cluster.name)

    LOG.info("Create cluster")
    client.cluster.create()

    LOG.info("Add nodes to cluster")
    rack = '/Default'
    client.nodes.add(all_hosts, rack, 'hadoop',
                     '/home/hadoop/.ssh/id_rsa')

    LOG.info("Install software")
    client.cluster.install_software(all_hosts)

    LOG.info("Configure services")
    _configure_services(client, cluster)

    LOG.info("Deploy cluster")
    client.nodes.config(force=True)

    LOG.info("Provisioning configs")
    # cinder and ephemeral drive support
    _configure_storage(client, cluster)
    # swift support
    _configure_swift(client, cluster)
    # user configs
    _add_user_params(client, cluster)

    LOG.info("Format HDFS")
    client.services.hdfs.format()


def _setup_oozie(cluster):
    with (u.get_oozie(cluster)).remote() as r:
        LOG.info("Oozie: add hadoop libraries to java.library.path")
        r.execute_command(
            "sudo ln -s /usr/lib/hadoop/lib/native/Linux-amd64-64/libhadoop.so"
            " /usr/lib64/ && "
            "sudo ln -s /usr/lib/hadoop/lib/native/Linux-amd64-64/libsnappy.so"
            " /usr/lib64/")

        ext22 = c_helper.get_config_value(
            cluster.cluster_configs.get('general'), c_helper.OOZIE_EXT22_URL)
        if ext22:
            LOG.info("Oozie: downloading and installing ext 2.2 from '%s'"
                     % ext22)
            r.execute_command(
                "curl -L -o ext-2.2.zip %s && "
                "sudo unzip ext-2.2.zip -d /var/lib/oozie && "
                "rm ext-2.2.zip" % ext22)

        LOG.info("Oozie: installing oozie share lib")
        r.execute_command(
            "mkdir /tmp/oozielib && "
            "tar xzf /usr/lib/oozie/oozie-sharelib.tar.gz -C /tmp/oozielib && "
            "rm /tmp/oozielib/share/lib/pig/pig-0.11.1-Intel.jar &&"
            "cp /usr/lib/pig/pig-0.11.1-Intel.jar "
            "/tmp/oozielib/share/lib/pig/pig-0.11.1-Intel.jar && "
            "sudo su - -c '"
            "hadoop fs -put /tmp/oozielib/share /user/oozie/share' hadoop && "
            "rm -rf /tmp/oozielib")


def start_cluster(cluster):
    client = c.IntelClient(u.get_instance(cluster, 'manager'), cluster.name)

    LOG.debug("Starting hadoop services")
    client.services.hdfs.start()

    if u.get_jobtracker(cluster):
        client.services.mapred.start()

    if u.get_hiveserver(cluster):
        client.services.hive.start()

    if u.get_oozie(cluster):
        LOG.info("Setup oozie")
        _setup_oozie(cluster)

        client.services.oozie.start()


def scale_cluster(cluster, instances):
    scale_ins_hosts = [i.fqdn() for i in instances]
    dn_hosts = [dn.fqdn() for dn in u.get_datanodes(cluster)]
    tt_hosts = [tt.fqdn() for tt in u.get_tasktrackers(cluster)]
    to_scale_dn = []
    to_scale_tt = []
    for i in scale_ins_hosts:
        if i in dn_hosts:
            to_scale_dn.append(i)

        if i in tt_hosts:
            to_scale_tt.append(i)

    client = c.IntelClient(u.get_instance(cluster, 'manager'), cluster.name)
    rack = '/Default'
    client.nodes.add(scale_ins_hosts, rack, 'hadoop',
                     '/home/hadoop/.ssh/id_rsa')
    client.cluster.install_software(scale_ins_hosts)

    if to_scale_tt:
        client.services.mapred.add_nodes('TaskTracker', to_scale_tt)

    if to_scale_dn:
        client.services.hdfs.add_nodes('DataNode', to_scale_dn)

    client.nodes.config()

    if to_scale_dn:
        client.services.hdfs.start()

    if to_scale_tt:
        client.services.mapred.start()


def decommission_nodes(cluster, instances):
    dec_hosts = [i.fqdn() for i in instances]
    dn_hosts = [dn.fqdn() for dn in u.get_datanodes(cluster)]
    tt_hosts = [dn.fqdn() for dn in u.get_tasktrackers(cluster)]

    client = c.IntelClient(u.get_instance(cluster, 'manager'), cluster.name)

    dec_dn_hosts = []
    for dec_host in dec_hosts:
        if dec_host in dn_hosts:
            dec_dn_hosts.append(dec_host)

    if dec_dn_hosts:
        client.services.hdfs.decommission_nodes(dec_dn_hosts)

        #TODO(alazarev) make timeout configurable (bug #1262897)
        timeout = 14400  # 4 hours
        cur_time = 0
        for host in dec_dn_hosts:
            while cur_time < timeout:
                if client.services.hdfs.get_datanode_status(
                        host) == 'Decomissioned':
                    break
                context.sleep(5)
                cur_time += 5
            else:
                LOG.warn("Failed to decomission node '%s' of cluster '%s' "
                         "in %s minutes" % (host, cluster.name, timeout / 60))

    client.nodes.stop(dec_hosts)

    # wait stop services
    #TODO(alazarev) make timeout configurable (bug #1262897)
    timeout = 600  # 10 minutes
    cur_time = 0
    for instance in instances:
        while cur_time < timeout:
            stopped = True
            if instance.fqdn() in dn_hosts:
                code, out = instance.remote().execute_command(
                    'sudo /sbin/service hadoop-datanode status',
                    raise_when_error=False)
                if out.strip() != 'datanode is stopped':
                    stopped = False
                if out.strip() == 'datanode dead but pid file exists':
                    instance.remote().execute_command(
                        'sudo rm -f '
                        '/var/run/hadoop/hadoop-hadoop-datanode.pid')
            if instance.fqdn() in tt_hosts:
                code, out = instance.remote().execute_command(
                    'sudo /sbin/service hadoop-tasktracker status',
                    raise_when_error=False)
                if out.strip() != 'tasktracker is stopped':
                    stopped = False
            if stopped:
                break
            else:
                context.sleep(5)
                cur_time += 5
        else:
            LOG.warn("Failed to stop services on node '%s' of cluster '%s' "
                     "in %s minutes" % (instance, cluster.name, timeout / 60))

    for node in dec_hosts:
        LOG.info("Deleting node '%s' on cluster '%s'" % (node, cluster.name))
        client.nodes.delete(node)
