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
