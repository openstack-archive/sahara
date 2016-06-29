# Copyright (c) 2014 Hoang Do, Phuc Vo, P. Michiardi, D. Venzano
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

from sahara import conductor as c
from sahara import exceptions as ex
from sahara.i18n import _


conductor = c.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_config_value(service, name, cluster=None):
    if cluster:
        for ng in cluster.node_groups:
            if (ng.configuration().get(service) and
                    ng.configuration()[service].get(name)):
                return ng.configuration()[service][name]

    raise ex.ConfigurationError(
        _("Unable to get parameter '%(param_name)s' from "
          "service %(service)s") % {'param_name': name, 'service': service})


def get_plugin_configs():
    return {}


def generate_storm_config(master_hostname, zk_hostnames, version):

    if version == '1.0.1':
        host_cfg = 'nimbus.seeds'
        master_value = [master_hostname.encode('ascii', 'ignore')]
    else:
        host_cfg = 'nimbus.host'
        master_value = master_hostname.encode('ascii', 'ignore')

    cfg = {
        host_cfg: master_value,
        "worker.childopts": "-Xmx768m -Djava.net.preferIPv4Stack=true",
        "nimbus.childopts": "-Xmx1024m -Djava.net.preferIPv4Stack=true",
        "supervisor.childopts": "-Djava.net.preferIPv4Stack=true",
        "storm.zookeeper.servers": [i.encode('ascii', 'ignore')
                                    for i in zk_hostnames],
        "ui.childopts": "-Xmx768m -Djava.net.preferIPv4Stack=true",
        "storm.local.dir": "/app/storm"
    }

    return cfg


def generate_slave_supervisor_conf():
    separator = "\n"
    conf = ("[program:storm-supervisor]",
            'command=bash -exec "cd /usr/local/storm && bin/storm supervisor"',
            "user=storm",
            "autostart=true",
            "autorestart=true",
            "startsecs=10",
            "startretries=999",
            "log_stdout=true",
            "log_stderr=true",
            "logfile=/var/log/storm/supervisor.out",
            "logfile_maxbytes=20MB",
            "logfile_backups=10")

    return separator.join(conf)


def generate_master_supervisor_conf():
    separator = "\n"
    seq_n = ("[program:storm-nimbus]",
             "command=/usr/local/storm/bin/storm nimbus",
             "user=storm",
             "autostart=true",
             "autorestart=true",
             "startsecs=10",
             "startretries=999",
             "log_stdout=true",
             "log_stderr=true",
             "logfile=/var/log/storm/supervisor.out",
             "logfile_maxbytes=20MB",
             "logfile_backups=10")

    seq_u = ("[program:storm-ui]",
             "command=/usr/local/storm/bin/storm ui",
             "user=storm",
             "autostart=true",
             "autorestart=true",
             "startsecs=10",
             "startretries=999",
             "log_stdout=true",
             "log_stderr=true",
             "logfile=/var/log/storm/ui.out",
             "logfile_maxbytes=20MB",
             "logfile_backups=10")

    conf_n = separator.join(seq_n)
    conf_u = separator.join(seq_u)
    conf = (conf_n, conf_u)

    return separator.join(conf)


def generate_zookeeper_conf():
    separator = "\n"
    conf = ("tickTime=2000",
            "dataDir=/var/zookeeper",
            "clientPort=2181")

    return separator.join(conf)


def generate_storm_setup_script(env_configs):
    separator = "\n"
    script_lines = ["#!/bin/bash -x"]
    script_lines.append("echo -n > /usr/local/storm/conf/storm.yaml")
    for line in env_configs:
        script_lines.append('echo "%s" >> /usr/local/storm/conf/storm.yaml'
                            % line)

    return separator.join(script_lines)


def extract_name_values(configs):
    return {cfg['name']: cfg['value'] for cfg in configs}


def _set_config(cfg, gen_cfg, name=None):
    if name in gen_cfg:
        cfg.update(gen_cfg[name]['conf'])
    if name is None:
        for name in gen_cfg:
            cfg.update(gen_cfg[name]['conf'])
    return cfg
