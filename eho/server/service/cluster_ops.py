import time
from novaclient.v1_1 import client as nova_client
from paramiko import SSHClient, AutoAddPolicy 

def _create_nova_client():
  return nova_client.Client("admin", "nova", "admin", "http://172.18.79.139:5000/v2.0/")

def _check_finding(entity, attr, value):
  if entity == None:
    raise RuntimeError("Unable to find entity with %s \'%s\'" %(attr, value))

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

def _connect_to_node(ssh, node):
  ssh.set_missing_host_key_policy(AutoAddPolicy())
  #ssh.connect(node['ip'], username='ubuntu', key_filename='/home/dmitryme/.ssh/srtlab-eho')
  ssh.connect(node['ip'], username='root', password='swordfish')

def launch_cluster(cluster):
  nova_client = _create_nova_client()

  clmap = dict()
  clmap['id'] = cluster.id
  clmap['name'] = cluster.name
  clmap['image'] = _find_by_id(nova_client.images.list(), cluster.base_image_id)
  _check_finding(clmap['image'], 'id', cluster.base_image_id)

  clmap['nodes'] = []
  num = 1

  for nc in cluster.node_counts:
    configs = dict()
    for cf in nc.node_template.node_template_configs:
      name = cf.node_process_property.name
      configs[name] = cf.value

    ntype = nc.node_template.node_type.name
    flv_id = nc.node_template.flavor_id
    flv = _find_by_id(nova_client.flavors.list(), flv_id)
    _check_finding(flv, 'id', flv_id)

    for i in xrange(0, nc.count):
      node = dict()
      node['name'] = '%s-%i' %(cluster.name, num)
      num += 1
      node['type'] = ntype
      node['flavor'] = flv
      node['configs'] = configs
      node['isup'] = False
      clmap['nodes'].append(node)

  print clmap

#  for node in clmap['nodes']:
#    _launch_node(nova_client, node['name'], node['flavor'], clmap['image'])

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

def _launch_node(nova_client, name, flavor, image):
  #nova_client.servers.create(name, image, flavor, key_name='srtlab-eho')
  nova_client.servers.create(name, image, flavor)

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

  ssh = SSHClient()
  try:
    _connect_to_node(ssh, node)
    ssh.exec_command('ls -l /')
  except:
    # ssh not ready yet
    # TODO log error if it takes more than 5 minutes to start-up
    return
  finally:
    ssh.close()

  node['isup'] = True

def _pre_cluster_setup(clmap):
  master = None
  slaves = []
  for node in clmap['nodes']:
    if node['type'] == 'jt+nn':
      master = node['ip']
    elif node['type'] == 'tt+dn':
      slaves.append(node['ip'])

  if master == None:
    raise RuntimeError("No master node is defined in the cluster")

  clmap['master'] = master
  clmap['slaves'] = slaves

def _sed_escape(s):
  result = ''
  for ch in s:
    if (ch == '/'):
      result += "\\\\"
    result += ch
  return result

def _prepare_config_cmd(filename, configs):
  command = 'cat %s.eho_template' %filename
  for key, value in configs.items():
    command += ' | sed -e \"s/%s/%s/g\"' %(_sed_escape(key), _sed_escape(value))

  return command + ' | tee %s' %filename

def _wrap_command(command):
  result = ' && echo -e \"Running\\n%s\\n-------------------------\" >> /tmp/eho_setup_log' %command
  return result + ' && ' + command + ' >> /tmp/eho_setup_log 2>&1"'

def _setup_node(node, clmap):
  ssh = SSHClient()

  _connect_to_node(ssh, node)

  node['configs']['%%%hdfs_namenode_url%%%'] = 'hdfs://%s:8020' %clmap['master']
  node['configs']['%%%mapred_jobtracker_url%%%'] = '%s:8021' %clmap['master']
  cmd = 'echo 1'
  command = _prepare_config_cmd('/etc/hadoop/core-site.xml', node['configs'])
  cmd += _wrap_command(command)
  command = _prepare_config_cmd('/etc/hadoop/mapred-site.xml', node['configs'])
  cmd += _wrap_command(command)

  command = '/etc/hadoop/create_dirs.sh'
  cmd += _wrap_command(command)


  if node['type'] == 'jt+nn':
    command = 'echo -e "'
    for slave in clmap['slaves']:
      command += slave + '\\n'
    command += '" > /etc/hadoop/slaves'
    cmd += _wrap_command(command)

    command = 'echo %s > /etc/hadoop/masters' %node['ip']
    cmd += _wrap_command(command)

    command = 'su -c \'hadoop namenode -format -force\' hadoop'
    cmd += _wrap_command(command)

    cmd += "echo \"-lastline-\""

  inp, outp, err = ssh.exec_command(cmd)
  while outp.readline().find("-lastline-")  == -1:
    pass

  ssh.close()
