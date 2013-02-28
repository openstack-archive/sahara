import logging
import time

from novaclient.v1_1 import client as nova_client
from paramiko import SSHClient, AutoAddPolicy
from eho.server.storage.models import Node, ServiceUrl

from eho.server.storage.storage import DB


def _create_nova_client():
    return nova_client.Client("admin", "nova", "admin",
                              "http://172.18.79.139:5000/v2.0/")


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

#def _connect_to_node(ssh, host):
#  ssh.set_missing_host_key_policy(AutoAddPolicy())
#  ssh.connect(host, username='root', password='swordfish')


def _execute_command_on_node(host, cmd):
    ssh = SSHClient()
    try:
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(host, username='root', password='swordfish')
        chan = ssh.get_transport().open_session()
        chan.exec_command(cmd)
        return chan.recv_exit_status()
    finally:
        ssh.close()


def launch_cluster(cluster):
    nova = _create_nova_client()

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
            node['name'] = '%s-%i' % (cluster.name, num)
            num += 1
            node['type'] = ntype
            node['templ_id'] = templ_id
            node['flavor'] = flv
            node['configs'] = configs
            node['isup'] = False
            clmap['nodes'].append(node)

    for node in clmap['nodes']:
        logging.debug("Starting node for cluster '%s', node: %s, iamge: %s",
                      cluster.name, node, clmap['image'])
        _launch_node(nova, node, clmap['image'])

    all_set = False

    logging.debug("All nodes for cluster '%s' has been started, waiting isup",
                  cluster.name)

    while not all_set:
        all_set = True

        for node in clmap['nodes']:
            _check_if_up(nova, node)

            if not node['isup']:
                all_set = False

        time.sleep(1)

    logging.debug("All nodes of cluster '%s' are up: %s",
                  cluster.name, all_set)

    _pre_cluster_setup(clmap)
    for node in clmap['nodes']:
        _setup_node(node, clmap)
        _register_node(node, cluster)

    logging.debug("All nodes of cluster '%s' are configured and registered, "
                  "starting cluster...", cluster.name)

    _start_cluster(cluster, clmap)


def _launch_node(nova, node, image):
    srv = nova.servers.create(node['name'], image, node['flavor'])
    #srv = _find_by_name(nova_client.servers.list(), node['name'])
    node['id'] = srv.id


def _check_if_up(nova, node):
    if node['isup']:
        # all set
        return

    if not 'ip' in node:
        srv = _find_by_name(nova.servers.list(), node['name'])
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
    except Exception:
        # ssh not ready yet
        # TODO log error if it takes more than 5 minutes to start-up
        return

    node['isup'] = True


def _pre_cluster_setup(clmap):
    clmap['master'] = None
    clmap['slaves'] = []
    for node in clmap['nodes']:
        if node['type'] == 'JT+NN':
            clmap['master'] = node['ip']
            clmap['master_internal'] = node['ip_internal']
        elif node['type'] == 'TT+DN':
            clmap['slaves'].append((node['ip'], node['ip_internal']))

    if clmap['master'] is None:
        raise RuntimeError("No master node is defined in the cluster")


def _sed_escape(line):
    result = ''
    for ch in line:
        if ch == '/':
            result += "\\\\"
        result += ch
    return result


def _prepare_config_cmd(filename, configs):
    command = 'cat %s.eho_template' % filename
    for key, value in configs.items():
        command += ' | sed -e "s/%s/%s/g" 2>&1' \
                   % (_sed_escape(key), _sed_escape(value))

    return command + ' | tee %s' % filename


def escape_doublequotes(line):
    result = ""
    for ch in line:
        if ch == '"':
            result += "\\"
        result += ch
    return result


def _wrap_command(command):
    result = ' ; echo -e \"-------------------------------\\n[$(date)] ' \
             'Running\\n%s\\n\" >> /tmp/eho_setup_log' \
             % escape_doublequotes(command)
    return result + ' ; ' + command + ' >> /tmp/eho_setup_log 2>&1'


def debug(line):
    fl = open('/tmp/mydebug', 'at')
    fl.write(str(line) + "\n")
    fl.close()


def _setup_node(node, clmap):
    node['configs']['%%%hdfs_namenode_url%%%'] = 'hdfs://%s:8020' \
                                                 % clmap['master_internal']
    node['configs']['%%%mapred_jobtracker_url%%%'] = '%s:8021' \
                                                     % clmap['master_internal']
    cmd = 'echo 123'
    command = _prepare_config_cmd('/etc/hadoop/core-site.xml',
                                  node['configs'])
    cmd += _wrap_command(command)
    command = _prepare_config_cmd('/etc/hadoop/mapred-site.xml',
                                  node['configs'])
    cmd += _wrap_command(command)

    command = '/etc/hadoop/create_dirs.sh'
    cmd += _wrap_command(command)

    if node['type'] == 'JT+NN':
        command = 'echo -e "'
        for slave in clmap['slaves']:
            command += slave[1] + '\\n'
        command += '" | tee /etc/hadoop/slaves'
        cmd += _wrap_command(command)

        command = 'echo \'%s\' | tee /etc/hadoop/masters' % node['ip_internal']
        cmd += _wrap_command(command)

        command = 'su -c \'hadoop namenode -format -force\' hadoop'
        cmd += _wrap_command(command)

    ret = _execute_command_on_node(node['ip'], cmd)
    _ensure_zero(ret)


def _register_node(node, cluster):
    debug(node['templ_id'])
    node_obj = Node(node['id'], cluster.id, node['templ_id'])
    srv_url_jt = ServiceUrl(cluster.id, 'jobtracker', 'http://%s:50030'
                                                      % node['ip'])
    srv_url_nn = ServiceUrl(cluster.id, 'namenode', 'http://%s:50070'
                                                    % node['ip'])

    DB.session.add(node_obj)
    DB.session.add(srv_url_jt)
    DB.session.add(srv_url_nn)

    DB.session.commit()


def _start_cluster(cluster, clmap):
    ret = _execute_command_on_node(clmap['master'],
                                   'su -c /usr/sbin/start-all.sh hadoop')
    _ensure_zero(ret)

    logging.info("Cluster '%s' successfully started!", cluster.name)


def stop_cluster(cluster):
    nova = _create_nova_client()

    for node in cluster.nodes:
        nova.servers.delete(node.vm_id)
        logging.debug("VM '%s' has been stopped", node.vm_id)
