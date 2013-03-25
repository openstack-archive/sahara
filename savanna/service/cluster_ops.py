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

import time

from jinja2 import Environment
from jinja2 import PackageLoader
from paramiko import SSHClient, AutoAddPolicy
from oslo.config import cfg
from savanna.storage.models import Node, ServiceUrl
from savanna.storage.db import DB
from savanna.utils.openstack.nova import novaclient
from savanna.openstack.common import log as logging


LOG = logging.getLogger(__name__)

CONF = cfg.CONF

cluster_node_opts = [
    cfg.StrOpt('username',
               default='root',
               help='An existing user on Hadoop image'),
    cfg.StrOpt('password',
               default='swordfish',
               help='User\'s password')
]

CONF.register_opts(cluster_node_opts, 'cluster_node')
#CONF.import_opt('nova_internal_net_name', 'savanna.main')


def _find_by_id(lst, id):
    for entity in lst:
        if entity.id == id:
            return entity

    return None


def _find_by_name(lst, name):
    for entity in lst:
        if entity.name == name:
            return entity

    return None


def _check_finding(entity, attr, value):
    if entity is None:
        raise RuntimeError("Unable to find entity with %s "
                           "\'%s\'" % (attr, value))


def _ensure_zero(ret):
    if ret != 0:
        raise RuntimeError('Command returned non-zero status code - %i' % ret)


def _setup_ssh_connection(host, ssh):
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(
        host,
        username=CONF.cluster_node.username,
        password=CONF.cluster_node.password
    )


def _open_channel_and_execute(ssh, cmd):
    chan = ssh.get_transport().open_session()
    chan.exec_command(cmd)
    return chan.recv_exit_status()


def _execute_command_on_node(host, cmd):
    ssh = SSHClient()
    try:
        _setup_ssh_connection(host, ssh)
        return _open_channel_and_execute(ssh, cmd)
    finally:
        ssh.close()


def launch_cluster(headers, cluster):
    nova = novaclient(headers)

    clmap = dict()
    clmap['id'] = cluster.id
    clmap['name'] = cluster.name
    clmap['image'] = _find_by_id(nova.images.list(),
                                 cluster.base_image_id)
    _check_finding(clmap['image'], 'id', cluster.base_image_id)

    clmap['nodes'] = []
    num = 1

    for nc in cluster.node_counts:
        configs = dict()
        for cf in nc.node_template.node_template_configs:
            name = cf.node_process_property.name
            configs[name] = cf.value

        ntype = nc.node_template.node_type.name
        templ_id = nc.node_template.id
        flv_id = nc.node_template.flavor_id
        flv = _find_by_name(nova.flavors.list(), flv_id)
        _check_finding(flv, 'id', flv_id)

        for _ in xrange(0, nc.count):
            node = dict()
            if ntype == 'JT+NN':
                node['name'] = '%s-master' % cluster.name
            else:
                node['name'] = '%s-%i' % (cluster.name, num)
                num += 1
            node['type'] = ntype
            node['templ_id'] = templ_id
            node['flavor'] = flv
            node['configs'] = configs
            node['is_up'] = False
            clmap['nodes'].append(node)

    for node in clmap['nodes']:
        LOG.debug("Starting node for cluster '%s', node: %s, iamge: %s",
                  cluster.name, node, clmap['image'])
        _launch_node(nova, node, clmap['image'])

    all_set = False

    LOG.debug("All nodes for cluster '%s' have been started, "
              "waiting for them to come up", cluster.name)

    while not all_set:
        all_set = True

        for node in clmap['nodes']:
            _check_if_up(nova, node)

            if not node['is_up']:
                all_set = False

        time.sleep(1)

    LOG.debug("All nodes of cluster '%s' are up: %s",
              cluster.name, all_set)

    _pre_cluster_setup(clmap)
    for node in clmap['nodes']:
        _setup_node(node, clmap)
        _register_node(node, cluster)

    LOG.debug("All nodes of cluster '%s' are configured and registered, "
              "starting the cluster...", cluster.name)

    _start_cluster(cluster, clmap)


def _launch_node(nova, node, image):
    srv = nova.servers.create(node['name'], image, node['flavor'])
    #srv = _find_by_name(nova_client.servers.list(), node['name'])
    node['id'] = srv.id


def _check_if_up(nova, node):
    if node['is_up']:
        # all set
        return

    if not 'ip' in node:
        srv = _find_by_id(nova.servers.list(), node['id'])
        nets = srv.networks

        if not CONF.nova_internal_net_name in nets:
            # VM's networking is not configured yet
            return

        ips = nets[CONF.nova_internal_net_name]
        if len(ips) < 2:
            # public IP is not assigned yet
            return

        # we assume that public floating IP comes last in the list
        node['ip'] = ips[-1]

    try:
        ret = _execute_command_on_node(node['ip'], 'ls -l /')
        _ensure_zero(ret)
    except Exception:
        # ssh is not up yet
        # TODO log error if it takes more than 5 minutes to start-up
        return

    node['is_up'] = True


def _render_template(template_name, **kwargs):
    env = Environment(loader=PackageLoader('savanna', '..'))
    templ = env.get_template('resources/%s.template' % template_name)
    return templ.render(**kwargs)


def _pre_cluster_setup(clmap):
    clmap['master_ip'] = None
    clmap['slaves'] = []
    for node in clmap['nodes']:
        if node['type'] == 'JT+NN':
            clmap['master_ip'] = node['ip']
            clmap['master_hostname'] = node['name']
            node['is_master'] = True
        elif node['type'] == 'TT+DN':
            clmap['slaves'].append(node['name'])
            node['is_master'] = False

    if clmap['master_ip'] is None:
        raise RuntimeError("No master node is defined in the cluster")

    configfiles = ['/etc/hadoop/core-site.xml',
                   '/etc/hadoop/mapred-site.xml']

    configs = [
        ('%%%hdfs_namenode_url%%%', 'hdfs:\\/\\/%s:8020'
                                    % clmap['master_hostname']),
        ('%%%mapred_jobtracker_url%%%', '%s:8021' % clmap['master_hostname'])
    ]

    templ_args = {'configfiles': configfiles,
                  'configs': configs,
                  'slaves': clmap['slaves'],
                  'master_hostname': clmap['master_hostname']}

    clmap['slave_script'] = _render_template('setup-general.sh', **templ_args)
    clmap['master_script'] = _render_template('setup-master.sh', **templ_args)


def _setup_node(node, clmap):
    if node['is_master']:
        script_body = clmap['master_script']
    else:
        script_body = clmap['slave_script']

    ssh = SSHClient()
    try:
        _setup_ssh_connection(node['ip'], ssh)
        sftp = ssh.open_sftp()
        fl = sftp.file('/tmp/savanna-hadoop-init.sh', 'w')
        fl.write(script_body)
        fl.close()
        sftp.chmod('/tmp/savanna-hadoop-init.sh', 0500)

        ret = _open_channel_and_execute(ssh,
                                        '/tmp/savanna-hadoop-init.sh '
                                        '>> /tmp/savanna-hadoop-init.log 2>&1')
        _ensure_zero(ret)
    finally:
        ssh.close()


def _register_node(node, cluster):
    node_obj = Node(node['id'], cluster.id, node['templ_id'])
    DB.session.add(node_obj)

    if node['is_master']:
        srv_url_jt = ServiceUrl(cluster.id, 'jobtracker', 'http://%s:50030'
                                                          % node['ip'])
        srv_url_nn = ServiceUrl(cluster.id, 'namenode', 'http://%s:50070'
                                                        % node['ip'])

        DB.session.add(srv_url_jt)
        DB.session.add(srv_url_nn)

    DB.session.commit()


def _start_cluster(cluster, clmap):
    ret = _execute_command_on_node(clmap['master_ip'],
                                   'su -c /usr/sbin/start-all.sh hadoop')
    _ensure_zero(ret)

    LOG.info("Cluster '%s' successfully started!", cluster.name)


def stop_cluster(headers, cluster):
    nova = novaclient(headers)

    for node in cluster.nodes:
        try:
            nova.servers.delete(node.vm_id)
            LOG.debug("vm '%s' has been stopped", node.vm_id)
        except Exception, e:
            LOG.info("Can't stop vm '%s': %s", node.vm_id, e)
