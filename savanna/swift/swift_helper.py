import logging
import pkg_resources as pkg
import xml.dom.minidom as xml

from oslo.config import cfg

from savanna import context
from savanna import version


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
HADOOP_SWIFT_AUTH_URL = 'fs.swift.service.savanna.auth.url'
HADOOP_SWIFT_TENANT = 'fs.swift.service.savanna.tenant'


def _get_parsed_conf(file_name='swift/resources/conf-template.xml'):
    return xml.parse(pkg.resource_filename(
        version.version_info.package, file_name))


def _initialise_configs():
    configs = {}
    conf = _get_parsed_conf()
    property = conf.getElementsByTagName('property')
    for name_value in property:
        name = name_value.getElementsByTagName('name')[0].firstChild.nodeValue
        value = ''

        conf_value = name_value.getElementsByTagName('value')
        if conf_value:
            value = conf_value[0].firstChild.nodeValue

        configs[name] = value
    return configs


def _retrieve_auth_url():
    url = "{0}://{1}:{2}/v2.0/tokens/".format(
        CONF.os_auth_protocol, CONF.os_auth_host, CONF.os_auth_port)
    return url


def _retrieve_tenant():
    try:
        return context.current().headers['X-Tenant-Name']
    except RuntimeError:
        LOG.error("Cannot retrieve tenant for swift integration. "
                  "Stop cluster creation")
        #todo(slukjanov?) raise special error here
        raise RuntimeError("Cannot retrieve tenant for swift integration")


def get_configs_names():
    conf = _get_parsed_conf()
    properties = conf.getElementsByTagName("name")
    return [prop.childNodes[0].data for prop in properties]


def get_swift_configs():
    configs = _initialise_configs()
    configs[HADOOP_SWIFT_AUTH_URL] = _retrieve_auth_url()
    configs[HADOOP_SWIFT_TENANT] = _retrieve_tenant()
    result = dict((k, v) for k, v in configs.iteritems() if v)
    LOG.info("Swift would be integrated with the following "
             "params: %s", result)
    return result
