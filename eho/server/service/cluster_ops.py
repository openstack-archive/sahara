import logging
import time
from eho.server.utils.openstack.nova import novaclient

from jinja2 import Environment
from jinja2 import PackageLoader

from paramiko import SSHClient, AutoAddPolicy

from eho.server.storage.models import Node, ServiceUrl
from eho.server.storage.storage import DB


NODE_CONF = {}


def setup_ops(app):
    NODE_CONF['user'] = app.config.get('NODE_USER')
    NODE_CONF['password'] = app.config.get('NODE_PASSWORD')
    NODE_CONF['vm_internal_net'] = \
        app.config.get('NODE_INTERNAL_NET')


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
        username=NODE_CONF['user'],
        password=NODE_CONF['password']
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
        logging.debug("Starting node for cluster '%s', node: %s, iamge: %s",
                      cluster.name, node, clmap['image'])
        _launch_node(nova, node, clmap['image'])

    all_set = False

    logging.debug("All nodes for cluster '%s' have been started, "
                  "waiting for them to come up", cluster.name)

    while not all_set:
        all_set = True

        for node in clmap['nodes']:
            _check_if_up(nova, node)

            if not node['is_up']:
                all_set = False

        time.sleep(1)

    logging.debug("All nodes of cluster '%s' are up: %s",
                  cluster.name, all_set)

    _pre_cluster_setup(clmap)
    for node in clmap['nodes']:
        _setup_node(node, clmap)
        _register_node(node, cluster)

    logging.debug("All nodes of cluster '%s' are configured and registered, "
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

        if not NODE_CONF['vm_internal_net'] in nets:
            # VM's networking is not configured yet
            return

        ips = nets[NODE_CONF['vm_internal_net']]
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
    env = Environment(loader=PackageLoader('eho', '..'))
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

    logging.info("Cluster '%s' successfully started!", cluster.name)


def stop_cluster(headers, cluster):
    nova = novaclient(headers)

    for node in cluster.nodes:
        try:
            nova.servers.delete(node.vm_id)
            logging.debug("vm '%s' has been stopped", node.vm_id)
        except Exception, e:
            logging.info("Can't stop vm '%s': %s", node.vm_id, e)
