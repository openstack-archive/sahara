# Copyright (c) 2015 Mirantis Inc.
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


import functools
import telnetlib  # nosec

from oslo_log import log as logging
from oslo_utils import uuidutils

from sahara import conductor
from sahara import context
from sahara.i18n import _LW
from sahara.plugins.ambari import client as ambari_client
from sahara.plugins.ambari import common as p_common
from sahara.plugins.ambari import configs
from sahara.plugins.ambari import ha_helper
from sahara.plugins import utils as plugin_utils
from sahara.utils import poll_utils


LOG = logging.getLogger(__name__)
conductor = conductor.API


repo_id_map = {
    "2.3": {
        "HDP": "HDP-2.3",
        "HDP-UTILS": "HDP-UTILS-1.1.0.20"
    }
}

os_type_map = {
    "centos6": "redhat6",
    "redhat6": "redhat6"
}


def setup_ambari(cluster):
    LOG.debug("Set up Ambari management console")
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    with ambari.remote() as r:
        sudo = functools.partial(r.execute_command, run_as_root=True)
        sudo("ambari-server setup -s -j"
             " `cut -f2 -d \"=\" /etc/profile.d/99-java.sh`", timeout=1800)
        sudo("service ambari-server start")
    LOG.debug("Ambari management console installed")


def setup_agents(cluster, instances=None):
    LOG.debug("Set up Ambari agents")
    manager_address = plugin_utils.get_instance(
        cluster, p_common.AMBARI_SERVER).fqdn()
    if not instances:
        instances = plugin_utils.get_instances(cluster)
    _setup_agents(instances, manager_address)


def _setup_agents(instances, manager_address):
    with context.ThreadGroup() as tg:
        for inst in instances:
            tg.spawn("hwx-agent-setup-%s" % inst.id,
                     _setup_agent, inst, manager_address)
    LOG.debug("Ambari agents have been installed")


def _disable_repos_on_inst(instance):
    with context.set_current_instance_id(instance_id=instance.instance_id):
        with instance.remote() as r:
            tmp_name = "/tmp/yum.repos.d-%s" % instance.instance_id[:8]
            sudo = functools.partial(r.execute_command, run_as_root=True)
            # moving to other folder
            sudo("mv /etc/yum.repos.d/ {fold_name}".format(
                fold_name=tmp_name))
            sudo("mkdir /etc/yum.repos.d")


def disable_repos(cluster):
    if configs.use_base_repos_needed(cluster):
        LOG.debug("Using base repos")
        return
    instances = plugin_utils.get_instances(cluster)
    with context.ThreadGroup() as tg:
        for inst in instances:
            tg.spawn("disable-repos-%s" % inst.instance_name,
                     _disable_repos_on_inst, inst)


def _setup_agent(instance, ambari_address):
    with instance.remote() as r:
        sudo = functools.partial(r.execute_command, run_as_root=True)
        r.replace_remote_string("/etc/ambari-agent/conf/ambari-agent.ini",
                                "localhost", ambari_address)
        sudo("service ambari-agent start")
        # for correct installing packages
        sudo("yum clean all")


def wait_ambari_accessible(cluster):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    kwargs = {"host": ambari.management_ip, "port": 8080}
    poll_utils.poll(_check_port_accessible, kwargs=kwargs, timeout=300)


def _check_port_accessible(host, port):
    try:
        conn = telnetlib.Telnet(host, port)
        conn.close()
        return True
    except IOError:
        return False


def _prepare_ranger(cluster):
    ranger = plugin_utils.get_instance(cluster, p_common.RANGER_ADMIN)
    if not ranger:
        return
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    with ambari.remote() as r:
        sudo = functools.partial(r.execute_command, run_as_root=True)
        sudo("yum install -y mysql-connector-java")
        sudo("ambari-server setup --jdbc-db=mysql "
             "--jdbc-driver=/usr/share/java/mysql-connector-java.jar")
    init_db_template = (
        "create user 'root'@'%' identified by '{password}';\n"
        "set password for 'root'@'localhost' = password('{password}');")
    password = uuidutils.generate_uuid()
    extra = cluster.extra.to_dict() if cluster.extra else {}
    extra["ranger_db_password"] = password
    ctx = context.ctx()
    conductor.cluster_update(ctx, cluster, {"extra": extra})
    with ranger.remote() as r:
        sudo = functools.partial(r.execute_command, run_as_root=True)
        # TODO(sreshetnyak): add ubuntu support
        sudo("yum install -y mysql-server")
        sudo("service mysqld start")
        r.write_file_to("/tmp/init.sql",
                        init_db_template.format(password=password))
        sudo("mysql < /tmp/init.sql")
        sudo("rm /tmp/init.sql")


def update_default_ambari_password(cluster):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    new_password = uuidutils.generate_uuid()
    with ambari_client.AmbariClient(ambari) as client:
        client.update_user_password("admin", "admin", new_password)
    extra = cluster.extra.to_dict() if cluster.extra else {}
    extra["ambari_password"] = new_password
    ctx = context.ctx()
    conductor.cluster_update(ctx, cluster, {"extra": extra})
    cluster = conductor.cluster_get(ctx, cluster.id)


def wait_host_registration(cluster, instances):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]
    with ambari_client.AmbariClient(ambari, password=password) as client:
        kwargs = {"client": client, "instances": instances}
        poll_utils.poll(_check_host_registration, kwargs=kwargs, timeout=600)


def _check_host_registration(client, instances):
    hosts = client.get_registered_hosts()
    registered_host_names = [h["Hosts"]["host_name"] for h in hosts]
    for instance in instances:
        if instance.fqdn() not in registered_host_names:
            return False
    return True


def set_up_hdp_repos(cluster):
    hdp_repo = configs.get_hdp_repo_url(cluster)
    hdp_utils_repo = configs.get_hdp_utils_repo_url(cluster)
    if not hdp_repo and not hdp_utils_repo:
        return
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]
    pv = cluster.hadoop_version
    repos = repo_id_map[pv]
    with ambari_client.AmbariClient(ambari, password=password) as client:
        os_type = os_type_map[client.get_host_info(ambari.fqdn())["os_type"]]
        if hdp_repo:
            client.set_up_mirror(pv, os_type, repos["HDP"], hdp_repo)
        if hdp_utils_repo:
            client.set_up_mirror(pv, os_type, repos["HDP-UTILS"],
                                 hdp_utils_repo)


def create_blueprint(cluster):
    _prepare_ranger(cluster)
    cluster = conductor.cluster_get(context.ctx(), cluster.id)
    host_groups = []
    for ng in cluster.node_groups:
        procs = p_common.get_ambari_proc_list(ng)
        procs.extend(p_common.get_clients(cluster))
        for instance in ng.instances:
            hg = {
                "name": instance.instance_name,
                "configurations": configs.get_instance_params(instance),
                "components": []
            }
            for proc in procs:
                hg["components"].append({"name": proc})
            host_groups.append(hg)
    bp = {
        "Blueprints": {
            "stack_name": "HDP",
            "stack_version": cluster.hadoop_version
        },
        "host_groups": host_groups,
        "configurations": configs.get_cluster_params(cluster)
    }
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]

    general_configs = cluster.cluster_configs.get("general", {})
    if (general_configs.get(p_common.NAMENODE_HA) or
            general_configs.get(p_common.RESOURCEMANAGER_HA) or
            general_configs.get(p_common.HBASE_REGIONSERVER_HA)):
        bp = ha_helper.update_bp_ha_common(cluster, bp)

    if general_configs.get(p_common.NAMENODE_HA):
        bp = ha_helper.update_bp_for_namenode_ha(cluster, bp)

    if general_configs.get(p_common.RESOURCEMANAGER_HA):
        bp = ha_helper.update_bp_for_resourcemanager_ha(cluster, bp)

    if general_configs.get(p_common.HBASE_REGIONSERVER_HA):
        bp = ha_helper.update_bp_for_hbase_ha(cluster, bp)

    with ambari_client.AmbariClient(ambari, password=password) as client:
        return client.create_blueprint(cluster.name, bp)


def _build_ambari_cluster_template(cluster):
    cl_tmpl = {
        "blueprint": cluster.name,
        "default_password": uuidutils.generate_uuid(),
        "host_groups": []
    }
    for ng in cluster.node_groups:
        for instance in ng.instances:
            cl_tmpl["host_groups"].append({
                "name": instance.instance_name,
                "hosts": [{"fqdn": instance.fqdn()}]
            })
    return cl_tmpl


def start_cluster(cluster):
    ambari_template = _build_ambari_cluster_template(cluster)

    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]
    with ambari_client.AmbariClient(ambari, password=password) as client:
        req_id = client.create_cluster(cluster.name, ambari_template)["id"]
        client.wait_ambari_request(req_id, cluster.name)


def add_new_hosts(cluster, instances):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]
    with ambari_client.AmbariClient(ambari, password=password) as client:
        for inst in instances:
            client.add_host_to_cluster(inst)


def manage_config_groups(cluster, instances):
    groups = []
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]
    for instance in instances:
        groups.extend(configs.get_config_group(instance))
    with ambari_client.AmbariClient(ambari, password=password) as client:
        client.create_config_group(cluster, groups)


def manage_host_components(cluster, instances):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]
    requests_ids = []
    with ambari_client.AmbariClient(ambari, password=password) as client:
        clients = p_common.get_clients(cluster)
        for instance in instances:
            services = p_common.get_ambari_proc_list(instance.node_group)
            services.extend(clients)
            for service in services:
                client.add_service_to_host(instance, service)
                requests_ids.append(
                    client.start_service_on_host(
                        instance, service, 'INSTALLED'))
        client.wait_ambari_requests(requests_ids, cluster.name)
        # all services added and installed, let's start them
        requests_ids = []
        for instance in instances:
            services = p_common.get_ambari_proc_list(instance.node_group)
            services.extend(p_common.ALL_LIST)
            for service in services:
                requests_ids.append(
                    client.start_service_on_host(
                        instance, service, 'STARTED'))
        client.wait_ambari_requests(requests_ids, cluster.name)


def decommission_hosts(cluster, instances):
    nodemanager_instances = filter(
        lambda i: p_common.NODEMANAGER in i.node_group.node_processes,
        instances)
    if len(nodemanager_instances) > 0:
        decommission_nodemanagers(cluster, nodemanager_instances)

    datanode_instances = filter(
        lambda i: p_common.DATANODE in i.node_group.node_processes,
        instances)
    if len(datanode_instances) > 0:
        decommission_datanodes(cluster, datanode_instances)


def decommission_nodemanagers(cluster, instances):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]

    with ambari_client.AmbariClient(ambari, password=password) as client:
        client.decommission_nodemanagers(cluster.name, instances)


def decommission_datanodes(cluster, instances):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]

    with ambari_client.AmbariClient(ambari, password=password) as client:
        client.decommission_datanodes(cluster.name, instances)


def restart_namenode(cluster, instance):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]

    with ambari_client.AmbariClient(ambari, password=password) as client:
        client.restart_namenode(cluster.name, instance)


def restart_resourcemanager(cluster, instance):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]

    with ambari_client.AmbariClient(ambari, password=password) as client:
        client.restart_resourcemanager(cluster.name, instance)


def restart_nns_and_rms(cluster):
    nns = plugin_utils.get_instances(cluster, p_common.NAMENODE)
    for nn in nns:
        restart_namenode(cluster, nn)

    rms = plugin_utils.get_instances(cluster, p_common.RESOURCEMANAGER)
    for rm in rms:
        restart_resourcemanager(cluster, rm)


def remove_services_from_hosts(cluster, instances):
    for inst in instances:
        LOG.debug("Stopping and removing processes from host %s" % inst.fqdn())
        _remove_services_from_host(cluster, inst)
        LOG.debug("Removing the host %s" % inst.fqdn())
        _remove_host(cluster, inst)


def _remove_services_from_host(cluster, instance):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]

    with ambari_client.AmbariClient(ambari, password=password) as client:
        hdp_processes = client.list_host_processes(cluster.name, instance)
        for proc in hdp_processes:
            LOG.debug("Stopping process %s on host %s " %
                      (proc, instance.fqdn()))
            client.stop_process_on_host(cluster.name, instance, proc)

            LOG.debug("Removing process %s from host %s " %
                      (proc, instance.fqdn()))
            client.remove_process_from_host(cluster.name, instance, proc)

    _wait_all_processes_removed(cluster, instance)


def _remove_host(cluster, inst):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]

    with ambari_client.AmbariClient(ambari, password=password) as client:
        client.delete_host(cluster.name, inst)


def _wait_all_processes_removed(cluster, instance):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]

    with ambari_client.AmbariClient(ambari, password=password) as client:
        while True:
            hdp_processes = client.list_host_processes(cluster.name, instance)
            if not hdp_processes:
                return
            context.sleep(5)


def add_hadoop_swift_jar(instances):
    new_jar = "/opt/hadoop-openstack.jar"
    for inst in instances:
        with inst.remote() as r:
            code, out = r.execute_command("test -f %s" % new_jar,
                                          raise_when_error=False)
            if code == 0:
                # get ambari hadoop version (e.g.: 2.7.1.2.3.4.0-3485)
                code, amb_hadoop_version = r.execute_command(
                    "sudo hadoop version | grep 'Hadoop' | awk '{print $2}'")
                amb_hadoop_version = amb_hadoop_version.strip()
                # get special code of ambari hadoop version(e.g.:2.3.4.0-3485)
                amb_code = '.'.join(amb_hadoop_version.split('.')[3:])
                origin_jar = (
                    "/usr/hdp/%s/hadoop-mapreduce/hadoop-openstack-%s.jar" % (
                        amb_code, amb_hadoop_version))
                r.execute_command("sudo cp %s %s" % (new_jar, origin_jar))
            else:
                LOG.warning(_LW("The {jar_file} file cannot be found "
                                "in the {dir} directory so Keystone API v3 "
                                "is not enabled for this cluster.")
                            .format(jar_file="hadoop-openstack.jar",
                                    dir="/opt"))
