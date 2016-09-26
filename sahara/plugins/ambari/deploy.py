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
from sahara.i18n import _
from sahara.i18n import _LW
from sahara.plugins.ambari import client as ambari_client
from sahara.plugins.ambari import common as p_common
from sahara.plugins.ambari import configs
from sahara.plugins.ambari import ha_helper
from sahara.plugins import kerberos
from sahara.plugins import utils as plugin_utils
from sahara.topology import topology_helper as t_helper
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import poll_utils


LOG = logging.getLogger(__name__)
conductor = conductor.API


repo_id_map = {
    "2.3": {
        "HDP": "HDP-2.3",
        "HDP-UTILS": "HDP-UTILS-1.1.0.20"
    },
    "2.4": {
        "HDP": "HDP-2.4",
        "HDP-UTILS": "HDP-UTILS-1.1.0.20"
    }
}

os_type_map = {
    "centos6": "redhat6",
    "redhat6": "redhat6",
    "centos7": "redhat7",
    "redhat7": "redhat7",
    "ubuntu14": "ubuntu14"
}


@cpo.event_wrapper(True, step=_("Set up Ambari management console"),
                   param=('cluster', 0))
def setup_ambari(cluster):
    LOG.debug("Set up Ambari management console")
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    with ambari.remote() as r:
        sudo = functools.partial(r.execute_command, run_as_root=True)
        sudo("rngd -r /dev/urandom -W 4096")
        sudo("ambari-server setup -s -j"
             " `cut -f2 -d \"=\" /etc/profile.d/99-java.sh`", timeout=1800)
        redirect_file = "/tmp/%s" % uuidutils.generate_uuid()
        sudo("service ambari-server start >{rfile} && "
             "cat {rfile} && rm {rfile}".format(rfile=redirect_file))
    LOG.debug("Ambari management console installed")


def setup_agents(cluster, instances=None):
    LOG.debug("Set up Ambari agents")
    manager_address = plugin_utils.get_instance(
        cluster, p_common.AMBARI_SERVER).fqdn()
    if not instances:
        instances = plugin_utils.get_instances(cluster)
    _setup_agents(instances, manager_address)


def _setup_agents(instances, manager_address):
    cpo.add_provisioning_step(
        instances[0].cluster.id, _("Set up Ambari agents"), len(instances))
    with context.ThreadGroup() as tg:
        for inst in instances:
            tg.spawn("hwx-agent-setup-%s" % inst.id,
                     _setup_agent, inst, manager_address)
    LOG.debug("Ambari agents have been installed")


def _disable_repos_on_inst(instance):
    with context.set_current_instance_id(instance_id=instance.instance_id):
        with instance.remote() as r:
            sudo = functools.partial(r.execute_command, run_as_root=True)
            if r.get_os_distrib() == "ubuntu":
                sudo("mv /etc/apt/sources.list /etc/apt/sources.list.tmp")
            else:
                tmp_name = "/tmp/yum.repos.d-%s" % instance.instance_id[:8]
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


@cpo.event_wrapper(True)
def _setup_agent(instance, ambari_address):
    with instance.remote() as r:
        sudo = functools.partial(r.execute_command, run_as_root=True)
        r.replace_remote_string("/etc/ambari-agent/conf/ambari-agent.ini",
                                "localhost", ambari_address)
        try:
            sudo("ambari-agent start")
        except Exception as e:
            # workaround for ubuntu, because on ubuntu the ambari agent
            # starts automatically after image boot
            msg = _("Restart of ambari-agent is needed for host {}, "
                    "reason: {}").format(instance.fqdn(), e)
            LOG.exception(msg)
            sudo("ambari-agent restart")
        # for correct installing packages
        r.update_repository()


@cpo.event_wrapper(True, step=_("Wait Ambari accessible"),
                   param=('cluster', 0))
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


def resolve_package_conflicts(cluster, instances=None):
    if not instances:
        instances = plugin_utils.get_instances(cluster)
    for instance in instances:
        with instance.remote() as r:
            if r.get_os_distrib() == 'ubuntu':
                try:
                    r.execute_command(
                        "apt-get remove -y libmysql-java", run_as_root=True)
                except Exception:
                    LOG.warning(_LW("Can't remove libmysql-java, "
                                    "it's probably not installed"))


def _prepare_ranger(cluster):
    ranger = plugin_utils.get_instance(cluster, p_common.RANGER_ADMIN)
    if not ranger:
        return
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    with ambari.remote() as r:
        sudo = functools.partial(r.execute_command, run_as_root=True)
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


@cpo.event_wrapper(True, step=_("Prepare Hive"), param=('cluster', 0))
def prepare_hive(cluster):
    hive = plugin_utils.get_instance(cluster, p_common.HIVE_SERVER)
    if not hive:
        return
    with hive.remote() as r:
        r.execute_command(
            'sudo su - -c  "hadoop fs -mkdir /user/oozie/conf" hdfs')
        r.execute_command(
            'sudo su - -c  "hadoop fs -copyFromLocal '
            '/etc/hive/conf/hive-site.xml '
            '/user/oozie/conf/hive-site.xml" hdfs')


@cpo.event_wrapper(True, step=_("Update default Ambari password"),
                   param=('cluster', 0))
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


@cpo.event_wrapper(True, step=_("Wait registration of hosts"),
                   param=('cluster', 0))
def wait_host_registration(cluster, instances):
    with _get_ambari_client(cluster) as client:
        kwargs = {"client": client, "instances": instances}
        poll_utils.poll(_check_host_registration, kwargs=kwargs, timeout=600)


def _check_host_registration(client, instances):
    hosts = client.get_registered_hosts()
    registered_host_names = [h["Hosts"]["host_name"] for h in hosts]
    for instance in instances:
        if instance.fqdn() not in registered_host_names:
            return False
    return True


@cpo.event_wrapper(True, step=_("Set up HDP repositories"),
                   param=('cluster', 0))
def _set_up_hdp_repos(cluster, hdp_repo, hdp_utils_repo):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    pv = cluster.hadoop_version
    repos = repo_id_map[pv]
    with _get_ambari_client(cluster) as client:
        os_type = os_type_map[client.get_host_info(ambari.fqdn())["os_type"]]
        if hdp_repo:
            client.set_up_mirror(pv, os_type, repos["HDP"], hdp_repo)
        if hdp_utils_repo:
            client.set_up_mirror(pv, os_type, repos["HDP-UTILS"],
                                 hdp_utils_repo)


def set_up_hdp_repos(cluster):
    hdp_repo = configs.get_hdp_repo_url(cluster)
    hdp_utils_repo = configs.get_hdp_utils_repo_url(cluster)
    if hdp_repo or hdp_utils_repo:
        _set_up_hdp_repos(cluster, hdp_repo, hdp_utils_repo)


def get_kdc_server(cluster):
    return plugin_utils.get_instance(
        cluster, p_common.AMBARI_SERVER)


def _prepare_kerberos(cluster, instances=None):
    if instances is None:
        kerberos.deploy_infrastructure(cluster, get_kdc_server(cluster))
        kerberos.prepare_policy_files(cluster)
    else:
        server = None
        if not kerberos.using_existing_kdc(cluster):
            server = get_kdc_server(cluster)
        kerberos.setup_clients(cluster, server)
        kerberos.prepare_policy_files(cluster)


def prepare_kerberos(cluster, instances=None):
    if kerberos.is_kerberos_security_enabled(cluster):
        _prepare_kerberos(cluster, instances)


def _serialize_mit_kdc_kerberos_env(cluster):
    return {
        'kerberos-env': {
            "realm": kerberos.get_realm_name(cluster),
            "kdc_type": "mit-kdc",
            "kdc_host": kerberos.get_kdc_host(
                cluster, get_kdc_server(cluster)),
            "admin_server_host": kerberos.get_kdc_host(
                cluster, get_kdc_server(cluster)),
            'encryption_types': 'aes256-cts-hmac-sha1-96',
            'ldap_url': '', 'container_dn': '',
        }
    }


def _serialize_krb5_configs(cluster):
    return {
        "krb5-conf": {
            "properties_attributes": {},
            "properties": {
                "manage_krb5_conf": "false"
            }
        }
    }


def _get_credentials(cluster):
    return [{
        "alias": "kdc.admin.credential",
        "principal": kerberos.get_admin_principal(cluster),
        "key": kerberos.get_server_password(cluster),
        "type": "TEMPORARY"
    }]


def get_host_group_components(cluster, processes):
    result = []
    for proc in processes:
        result.append({'name': proc})
    return result


@cpo.event_wrapper(True, step=_("Create Ambari blueprint"),
                   param=('cluster', 0))
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
                "components": get_host_group_components(cluster, procs)
            }
            host_groups.append(hg)
    bp = {
        "Blueprints": {
            "stack_name": "HDP",
            "stack_version": cluster.hadoop_version,
        },
        "host_groups": host_groups,
        "configurations": configs.get_cluster_params(cluster)
    }

    if kerberos.is_kerberos_security_enabled(cluster):
        bp['configurations'].extend([
            _serialize_mit_kdc_kerberos_env(cluster),
            _serialize_krb5_configs(cluster)
        ])
        bp['Blueprints']['security'] = {'type': 'KERBEROS'}

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

    with _get_ambari_client(cluster) as client:
        return client.create_blueprint(cluster.name, bp)


def _build_ambari_cluster_template(cluster):
    cl_tmpl = {
        "blueprint": cluster.name,
        "default_password": uuidutils.generate_uuid(),
        "host_groups": []
    }

    if cluster.use_autoconfig:
        strategy = configs.get_auto_configuration_strategy(cluster)
        cl_tmpl["config_recommendation_strategy"] = strategy

    if kerberos.is_kerberos_security_enabled(cluster):
        cl_tmpl["credentials"] = _get_credentials(cluster)
        cl_tmpl["security"] = {"type": "KERBEROS"}
    topology = _get_topology_data(cluster)
    for ng in cluster.node_groups:
        for instance in ng.instances:
            host = {"fqdn": instance.fqdn()}
            if t_helper.is_data_locality_enabled():
                host["rack_info"] = topology[instance.instance_name]
            cl_tmpl["host_groups"].append({
                "name": instance.instance_name,
                "hosts": [host]
            })
    return cl_tmpl


@cpo.event_wrapper(True, step=_("Start cluster"), param=('cluster', 0))
def start_cluster(cluster):
    ambari_template = _build_ambari_cluster_template(cluster)
    with _get_ambari_client(cluster) as client:
        req_id = client.create_cluster(cluster.name, ambari_template)["id"]
        client.wait_ambari_request(req_id, cluster.name)


@cpo.event_wrapper(True)
def _add_host_to_cluster(instance, client):
    client.add_host_to_cluster(instance)


def add_new_hosts(cluster, instances):
    with _get_ambari_client(cluster) as client:
        cpo.add_provisioning_step(
            cluster.id, _("Add new hosts"), len(instances))
        for inst in instances:
            _add_host_to_cluster(inst, client)


@cpo.event_wrapper(True, step=_("Generate config groups"),
                   param=('cluster', 0))
def manage_config_groups(cluster, instances):
    groups = []
    for instance in instances:
        groups.extend(configs.get_config_group(instance))
    with _get_ambari_client(cluster) as client:
        client.create_config_group(cluster, groups)


@cpo.event_wrapper(True, step=_("Cleanup config groups"),
                   param=('cluster', 0))
def cleanup_config_groups(cluster, instances):
    to_remove = set()
    for instance in instances:
        cfg_name = "%s:%s" % (cluster.name, instance.instance_name)
        to_remove.add(cfg_name)
    with _get_ambari_client(cluster) as client:
        config_groups = client.get_config_groups(cluster)
        for group in config_groups['items']:
            cfg_id = group['ConfigGroup']['id']
            detailed = client.get_detailed_config_group(cluster, cfg_id)
            cfg_name = detailed['ConfigGroup']['group_name']
            # we have config group per host
            if cfg_name in to_remove:
                client.remove_config_group(cluster, cfg_id)


@cpo.event_wrapper(True, step=_("Regenerate keytabs for Kerberos"),
                   param=('cluster', 0))
def _regenerate_keytabs(cluster):
    with _get_ambari_client(cluster) as client:
        alias = "kdc.admin.credential"
        try:
            client.get_credential(cluster.name, alias)
        except ambari_client.AmbariNotFound:
            # credentials are missing
            data = {
                'Credential': {
                    "principal": kerberos.get_admin_principal(cluster),
                    "key": kerberos.get_server_password(cluster),
                    "type": "TEMPORARY"
                }
            }

            client.import_credential(cluster.name, alias, data)

        req_id = client.regenerate_keytabs(cluster.name)
        client.wait_ambari_request(req_id, cluster.name)


@cpo.event_wrapper(True, step=_("Install services on hosts"),
                   param=('cluster', 0))
def _install_services_to_hosts(cluster, instances):
    requests_ids = []
    with _get_ambari_client(cluster) as client:
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


@cpo.event_wrapper(True, step=_("Start services on hosts"),
                   param=('cluster', 0))
def _start_services_on_hosts(cluster, instances):
    with _get_ambari_client(cluster) as client:
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


def manage_host_components(cluster, instances):
    _install_services_to_hosts(cluster, instances)
    if kerberos.is_kerberos_security_enabled(cluster):
        _regenerate_keytabs(cluster)
    _start_services_on_hosts(cluster, instances)


@cpo.event_wrapper(True, step=_("Decommission NodeManagers and DataNodes"),
                   param=('cluster', 0))
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
    with _get_ambari_client(cluster) as client:
        client.decommission_nodemanagers(cluster.name, instances)


def decommission_datanodes(cluster, instances):
    with _get_ambari_client(cluster) as client:
        client.decommission_datanodes(cluster.name, instances)


def restart_namenode(cluster, instance):
    with _get_ambari_client(cluster) as client:
        client.restart_namenode(cluster.name, instance)


def restart_resourcemanager(cluster, instance):
    with _get_ambari_client(cluster) as client:
        client.restart_resourcemanager(cluster.name, instance)


@cpo.event_wrapper(True, step=_("Restart NameNodes and ResourceManagers"),
                   param=('cluster', 0))
def restart_nns_and_rms(cluster):
    nns = plugin_utils.get_instances(cluster, p_common.NAMENODE)
    for nn in nns:
        restart_namenode(cluster, nn)

    rms = plugin_utils.get_instances(cluster, p_common.RESOURCEMANAGER)
    for rm in rms:
        restart_resourcemanager(cluster, rm)


def restart_service(cluster, service_name):
    with _get_ambari_client(cluster) as client:
        client.restart_service(cluster.name, service_name)


@cpo.event_wrapper(True, step=_("Remove hosts"), param=('cluster', 0))
def remove_services_from_hosts(cluster, instances):
    for inst in instances:
        LOG.debug("Stopping and removing processes from host %s" % inst.fqdn())
        _remove_services_from_host(cluster, inst)
        LOG.debug("Removing the host %s" % inst.fqdn())
        _remove_host(cluster, inst)


def _remove_services_from_host(cluster, instance):
    with _get_ambari_client(cluster) as client:
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
    with _get_ambari_client(cluster) as client:
        client.delete_host(cluster.name, inst)


def _wait_all_processes_removed(cluster, instance):
    with _get_ambari_client(cluster) as client:
        while True:
            hdp_processes = client.list_host_processes(cluster.name, instance)
            if not hdp_processes:
                return
            context.sleep(5)


def _get_ambari_client(cluster):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    password = cluster.extra["ambari_password"]
    return ambari_client.AmbariClient(ambari, password=password)


def _get_topology_data(cluster):
    if not t_helper.is_data_locality_enabled():
        return {}

    LOG.warning(_LW("Node group awareness is not implemented in YARN yet "
                    "so enable_hypervisor_awareness set to False "
                    "explicitly"))
    return t_helper.generate_topology_map(cluster, is_node_awareness=False)


@cpo.event_wrapper(True)
def _configure_topology_data(cluster, inst, client):
    topology = _get_topology_data(cluster)
    client.set_rack_info_for_instance(
        cluster.name, inst, topology[inst.instance_name])


@cpo.event_wrapper(True, step=_("Restart HDFS and MAPREDUCE2 services"),
                   param=('cluster', 0))
def _restart_hdfs_and_mapred_services(cluster, client):
    client.restart_service(cluster.name, p_common.HDFS_SERVICE)
    client.restart_service(cluster.name, p_common.MAPREDUCE2_SERVICE)


def configure_rack_awareness(cluster, instances):
    if not t_helper.is_data_locality_enabled():
        return

    with _get_ambari_client(cluster) as client:
        cpo.add_provisioning_step(
            cluster.id, _("Configure rack awareness"), len(instances))
        for inst in instances:
            _configure_topology_data(cluster, inst, client)
        _restart_hdfs_and_mapred_services(cluster, client)


@cpo.event_wrapper(True)
def _add_hadoop_swift_jar(instance, new_jar):
    with instance.remote() as r:
        code, out = r.execute_command(
            "test -f %s" % new_jar, raise_when_error=False)
        if code == 0:
            # get ambari hadoop version (e.g.: 2.7.1.2.3.4.0-3485)
            code, amb_hadoop_version = r.execute_command(
                "sudo hadoop version | grep 'Hadoop' | awk '{print $2}'")
            amb_hadoop_version = amb_hadoop_version.strip()
            # get special code of ambari hadoop version(e.g.:2.3.4.0-3485)
            amb_code = '.'.join(amb_hadoop_version.split('.')[3:])
            origin_jar = (
                "/usr/hdp/{}/hadoop-mapreduce/hadoop-openstack-{}.jar".format(
                    amb_code, amb_hadoop_version))
            r.execute_command("sudo cp {} {}".format(new_jar, origin_jar))
        else:
            LOG.warning(_LW("The {jar_file} file cannot be found "
                            "in the {dir} directory so Keystone API v3 "
                            "is not enabled for this cluster.")
                        .format(jar_file="hadoop-openstack.jar",
                                dir="/opt"))


def add_hadoop_swift_jar(instances):
    new_jar = "/opt/hadoop-openstack.jar"
    cpo.add_provisioning_step(instances[0].cluster.id,
                              _("Add Hadoop Swift jar to instances"),
                              len(instances))
    for inst in instances:
        _add_hadoop_swift_jar(inst, new_jar)


def deploy_kerberos_principals(cluster, instances=None):
    if not kerberos.is_kerberos_security_enabled(cluster):
        return
    if instances is None:
        instances = plugin_utils.get_instances(cluster)
    mapper = {
        'hdfs': plugin_utils.instances_with_services(
            instances, [p_common.SECONDARY_NAMENODE, p_common.NAMENODE,
                        p_common.DATANODE, p_common.JOURNAL_NODE]),
        'spark': plugin_utils.instances_with_services(
            instances, [p_common.SPARK_JOBHISTORYSERVER]),
        'oozie': plugin_utils.instances_with_services(
            instances, [p_common.OOZIE_SERVER]),
    }

    kerberos.create_keytabs_for_map(cluster, mapper)
