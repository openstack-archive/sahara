import time, logging

from jinja2 import Environment
from jinja2 import PackageLoader

from novaclient.v1_1 import client as nova_client
from paramiko import SSHClient, AutoAddPolicy

from eho.server.storage.models import *
from eho.server.storage.storage import db


def setup_ops():
    global OPENSTACK_USER, OPENSTACK_PASSWORD, OPENSTACK_TENANT, OPENSTACK_URL
    global NODE_USER, NODE_PASSWORD

    OPENSTACK_USER = 'admin'
    OPENSTACK_PASSWORD = 'nova'
    OPENSTACK_TENANT = 'admin'
    OPENSTACK_URL = 'http://172.18.79.139:5000/v2.0/'

    NODE_USER = 'root'
    NODE_PASSWORD = 'swordfish'


def _create_nova_client():
    return nova_client.Client(OPENSTACK_USER, OPENSTACK_PASSWORD,
                              OPENSTACK_TENANT, OPENSTACK_URL)


def _check_finding(entity, attr, value):
    if entity is None:
        raise RuntimeError("Unable to find entity with %s "
                           "\'%s\'" % (attr, value))


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


def _ensure_zero(ret):
    if ret != 0:
        raise RuntimeError('Command returned non-zero status code - %i' % ret)


def _setup_ssh_connection(host, ssh):
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(host, username=NODE_USER, password=NODE_PASSWORD)


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


def launch_cluster(cluster):
    nova_client = _create_nova_client()

    clmap = dict()
    clmap['id'] = cluster.id
    clmap['name'] = cluster.name
    clmap['image'] = _find_by_id(nova_client.images.list(),
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
        flv = _find_by_name(nova_client.flavors.list(), flv_id)
        _check_finding(flv, 'id', flv_id)

        for i in xrange(0, nc.count):
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
            node['isup'] = False
            clmap['nodes'].append(node)

    for node in clmap['nodes']:
        _launch_node(nova_client, node, clmap['image'])

    all_set = False

    while not all_set:
        all_set = True

        for node in clmap['nodes']:
            _check_if_up(nova_client, node)

            if not node['isup']:
                all_set = False

        time.sleep(1)

    _pre_cluster_setup(clmap)
    for node in clmap['nodes']:
        _setup_node(node, clmap)
        _register_node(node, cluster)

    _start_cluster(clmap)


def _launch_node(nova_client, node, image):
    srv = nova_client.servers.create(node['name'], image, node['flavor'])
    #srv = _find_by_name(nova_client.servers.list(), node['name'])
    node['id'] = srv.id


def _check_if_up(nova_client, node):
    if node['isup']:
        # all set
        return

    if not 'ip' in node:
        srv = _find_by_name(nova_client.servers.list(), node['name'])
        nets = srv.networks
        if not 'supernetwork' in nets:
            # it does not have interfaces yet
            return
        ips = nets['supernetwork']
        if len(ips) < 2:
            # public IP is not defined yet
            return
        node['ip'] = ips[-1]
        node['ip_internal'] = ips[0]

    try:
        ret = _execute_command_on_node(node['ip'], 'ls -l /')
        _ensure_zero(ret)
    except:
        # ssh not ready yet
        # TODO log error if it takes more than 5 minutes to start-up
        return

    node['isup'] = True


def _render_template(template_name, **kwargs):
    env = Environment(loader=PackageLoader('eho', '..'))
    templ = env.get_template('resources/%s.template' %template_name)
    return templ.render(**kwargs)


def _pre_cluster_setup(clmap):
    clmap['master'] = None
    clmap['slaves'] = []
    for node in clmap['nodes']:
        if node['type'] == 'JT+NN':
            clmap['master'] = node['ip']
            clmap['master_internal'] = node['ip_internal']
            clmap['master_hostname'] = node['name']
            node['is_master'] = True
        elif node['type'] == 'TT+DN':
            clmap['slaves'].append((node['ip'], node['name'], node['ip_internal']))
            node['is_master'] = False

    if clmap['master'] is None:
        raise RuntimeError("No master node is defined in the cluster")

    configfiles = ['/etc/hadoop/core-site.xml',
                   '/etc/hadoop/mapred-site.xml']

    configs = [('%%%hdfs_namenode_url%%%',
                'hdfs:\\/\\/%s:8020' % clmap['master_hostname']),
               ('%%%mapred_jobtracker_url%%%',
                '%s:8021' % clmap['master_hostname'])
    ]

    templ_args = {'configfiles': configfiles,
                     'configs': configs,
                     'slaves': clmap['slaves'],
                     'master_internal': clmap['master_hostname']}

    clmap['slave_script'] = _render_template('setup-general.sh', **templ_args)
    clmap['master_script'] = _render_template('setup-master.sh', **templ_args)


def _setup_node(node, clmap):
    if (node['ip'] == clmap['master']):
        script_body = clmap['master_script']
    else:
        script_body = clmap['slave_script']

    ssh = SSHClient()
    try:
        _setup_ssh_connection(node['ip'], ssh)
        sftp = ssh.open_sftp()
        fl = sftp.file('/tmp/eho-hadoop-init.sh', 'w')
        fl.write(script_body)
        fl.close()
        sftp.chmod('/tmp/eho-hadoop-init.sh', 0500)

        ret = _open_channel_and_execute(ssh, '/tmp/eho-hadoop-init.sh '
                                             '>>/tmp/eho-hadoop-init.log 2>&1')
        _ensure_zero(ret)
    finally:
        ssh.close()


def _register_node(node, cluster):
    node_obj = Node(node['id'], cluster.id, node['templ_id'])
    db.session.add(node_obj)

    if node['is_master']:
        srv_url_jt = ServiceUrl(cluster.id, 'jobtracker', 'http://%s:50030'
                                                          % node['ip'])
        srv_url_nn = ServiceUrl(cluster.id, 'namenode', 'http://%s:50070'
                                                        % node['ip'])

        db.session.add(srv_url_jt)
        db.session.add(srv_url_nn)

    db.session.commit()


def _start_cluster(clmap):
    ret = _execute_command_on_node(clmap['master'],
                                   'su -c /usr/sbin/start-all.sh hadoop')
    _ensure_zero(ret)
