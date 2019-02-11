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

from oslo_config import cfg
from oslo_log import log as logging

from sahara import conductor as cond
from sahara import context
from sahara.plugins import provisioning as common_configs
from sahara.utils import cluster as c_u


CONF = cfg.CONF

LOG = logging.getLogger(__name__)
conductor = cond.API

ntp_opts = [
    cfg.StrOpt('default_ntp_server',
               default="pool.ntp.org",
               help="Default ntp server for time sync")
]

CONF.register_opts(ntp_opts)


def _sudo(remote, cmd):
    remote.execute_command(cmd, run_as_root=True)


def _restart_ntp(remote):
    distrib = remote.get_os_distrib()
    cmd = "service %s restart"
    if distrib == 'ubuntu':
        cmd = cmd % "ntp"
    else:
        cmd = cmd % "ntpd"

    _sudo(remote, cmd)


def _verify_installation(remote):
    distrib = remote.get_os_distrib()
    if distrib == 'ubuntu':
        return remote.execute_command("dpkg -s ntp")
    else:
        return remote.execute_command("rpm -q ntp")


def _check_ntp_installed(remote):
    try:
        exit_code, stdout = _verify_installation(remote)
        if exit_code != 0:
            return False
        return True
    except Exception:
        return False


def _configure_ntp_on_instance(instance, url):
    with context.set_current_instance_id(instance.instance_id):
        LOG.debug("Configuring ntp server")
        with instance.remote() as r:
            if not _check_ntp_installed(r):
                # missing ntp service
                LOG.warning("Unable to configure NTP service")
                return

            r.prepend_to_file(
                "/etc/ntp.conf", "server {url} iburst\n".format(url=url),
                run_as_root=True)
            _restart_ntp(r)
            try:
                _sudo(r, "ntpdate -u {url}".format(url=url))
            except Exception as e:
                LOG.debug("Update time on VM failed with error: %s", e)
            LOG.info("NTP successfully configured")


def is_ntp_enabled(cluster):
    target = common_configs.NTP_ENABLED.applicable_target
    name = common_configs.NTP_ENABLED.name
    cl_configs = cluster.cluster_configs
    if target not in cl_configs or name not in cl_configs[target]:
        return common_configs.NTP_ENABLED.default_value
    return cl_configs[target][name]


def retrieve_ntp_server_url(cluster):
    target = common_configs.NTP_URL.applicable_target
    name = common_configs.NTP_URL.name
    cl_configs = cluster.cluster_configs
    if target not in cl_configs or name not in cl_configs[target]:
        return CONF.default_ntp_server
    return cl_configs[target][name]


def configure_ntp(cluster_id, instance_ids=None):
    cluster = conductor.cluster_get(context.ctx(), cluster_id)
    if not is_ntp_enabled(cluster):
        LOG.debug("Don't configure NTP on cluster")
        return
    instances = c_u.get_instances(cluster, instance_ids)
    url = retrieve_ntp_server_url(cluster)
    with context.ThreadGroup() as tg:
        for instance in instances:
            tg.spawn("configure-ntp-%s" % instance.instance_name,
                     _configure_ntp_on_instance, instance, url)
