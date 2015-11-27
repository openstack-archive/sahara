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

from oslo_config import cfg
from oslo_log import log as logging

from sahara import context
from sahara.i18n import _LI
from sahara.swift import utils as su
from sahara.utils import xmlutils as x


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
HADOOP_SWIFT_AUTH_URL = 'fs.swift.service.sahara.auth.url'
HADOOP_SWIFT_TENANT = 'fs.swift.service.sahara.tenant'
HADOOP_SWIFT_USERNAME = 'fs.swift.service.sahara.username'
HADOOP_SWIFT_PASSWORD = 'fs.swift.service.sahara.password'
HADOOP_SWIFT_REGION = 'fs.swift.service.sahara.region'
HADOOP_SWIFT_TRUST_ID = 'fs.swift.service.sahara.trust.id'
HADOOP_SWIFT_DOMAIN_NAME = 'fs.swift.service.sahara.domain.name'

opts = [
    cfg.StrOpt("public_identity_ca_file",
               help=("Location of ca certificate file to use for identity "
                     "client requests via public endpoint")),
    cfg.StrOpt("public_object_store_ca_file",
               help=("Location of ca certificate file to use for object-store "
                     "client requests via public endpoint"))
]

public_endpoint_cert_group = cfg.OptGroup(
    name="object_store_access", title="Auth options for Swift access from VM")

CONF.register_group(public_endpoint_cert_group)
CONF.register_opts(opts, group=public_endpoint_cert_group)


def retrieve_tenant():
    return context.current().tenant_name


def get_swift_configs():
    configs = x.load_hadoop_xml_defaults('swift/resources/conf-template.xml')
    for conf in configs:
        if conf['name'] == HADOOP_SWIFT_AUTH_URL:
            conf['value'] = su.retrieve_auth_url() + "tokens/"
        if conf['name'] == HADOOP_SWIFT_TENANT:
            conf['value'] = retrieve_tenant()
        if CONF.os_region_name and conf['name'] == HADOOP_SWIFT_REGION:
            conf['value'] = CONF.os_region_name

    result = [cfg for cfg in configs if cfg['value']]
    LOG.info(_LI("Swift would be integrated with the following "
             "params: {result}").format(result=result))
    return result


def read_default_swift_configs():
    return x.load_hadoop_xml_defaults('swift/resources/conf-template.xml')


def install_ssl_certs(instances):
    certs = []
    if CONF.object_store_access.public_identity_ca_file:
        certs.append(CONF.object_store_access.public_identity_ca_file)
    if CONF.object_store_access.public_object_store_ca_file:
        certs.append(CONF.object_store_access.public_object_store_ca_file)
    if not certs:
        return
    with context.ThreadGroup() as tg:
        for inst in instances:
            tg.spawn("configure-ssl-cert-%s" % inst.instance_id,
                     _install_ssl_certs, inst, certs)


def _install_ssl_certs(instance, certs):
    register_cmd = (
        "sudo su - -c \"keytool -import -alias sahara-%d -keystore "
        "`cut -f2 -d \\\"=\\\" /etc/profile.d/99-java.sh | head -1`"
        "/lib/security/cacerts -file /tmp/cert.pem -noprompt -storepass "
        "changeit\"")
    with instance.remote() as r:
        for idx, cert in enumerate(certs):
            with open(cert) as cert_fd:
                data = cert_fd.read()
            r.write_file_to("/tmp/cert.pem", data)
            try:
                r.execute_command(register_cmd % idx)
            finally:
                r.execute_command("rm /tmp/cert.pem")
