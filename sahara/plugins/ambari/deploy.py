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
import telnetlib

from oslo_log import log as logging
from oslo_utils import uuidutils

from sahara import conductor
from sahara import context
from sahara.i18n import _
from sahara.plugins.ambari import client as ambari_client
from sahara.plugins.ambari import common as p_common
from sahara.plugins import exceptions as p_exc
from sahara.plugins import utils as plugin_utils
from sahara.utils import poll_utils


LOG = logging.getLogger(__name__)
conductor = conductor.API


def setup_ambari(cluster):
    LOG.debug("Set up Ambari management console")
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    with ambari.remote() as r:
        sudo = functools.partial(r.execute_command, run_as_root=True)
        sudo("ambari-server setup -s -j"
             " `cut -f2 -d \"=\" /etc/profile.d/99-java.sh`", timeout=1800)
        sudo("service ambari-server start")
    LOG.debug("Ambari management console installed")


def setup_agents(cluster):
    LOG.debug("Set up Ambari agents")
    manager_address = plugin_utils.get_instance(
        cluster, p_common.AMBARI_SERVER).fqdn()
    with context.ThreadGroup() as tg:
        for inst in plugin_utils.get_instances(cluster):
            tg.spawn("hwx-agent-setup-%s" % inst.id,
                     _setup_agent, inst, manager_address)
    LOG.debug("Ambari agents has been installed")


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


def wait_host_registration(cluster):
    ambari = plugin_utils.get_instance(cluster, p_common.AMBARI_SERVER)
    hosts = plugin_utils.get_instances(cluster)
    password = cluster.extra["ambari_password"]
    with ambari_client.AmbariClient(ambari, password=password) as client:
        kwargs = {"client": client, "num_hosts": len(hosts)}
        poll_utils.poll(_check_host_registration, kwargs=kwargs, timeout=600)
        registered_hosts = client.get_registered_hosts()
    registered_host_names = [h["Hosts"]["host_name"] for h in registered_hosts]
    actual_host_names = [h.fqdn() for h in hosts]
    if sorted(registered_host_names) != sorted(actual_host_names):
        raise p_exc.HadoopProvisionError(
            _("Host registration fails in Ambari"))


def _check_host_registration(client, num_hosts):
    hosts = client.get_registered_hosts()
    return len(hosts) == num_hosts
