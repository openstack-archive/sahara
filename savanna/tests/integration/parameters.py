import savanna.openstack.common.importutils as importutils

_CONF = importutils.try_import('savanna.tests.integration.config')


def _get_conf(key, default):
    return getattr(_CONF, key) if _CONF and hasattr(_CONF, key) else default

OS_USERNAME = _get_conf('OS_USERNAME', 'admin')
OS_PASSWORD = _get_conf('OS_PASSWORD', 'password')
OS_TENANT_NAME = _get_conf('OS_TENANT_NAME', 'admin')
OS_AUTH_URL = _get_conf('OS_AUTH_URL', 'http://192.168.1.1:35357/v2.0/')

SAVANNA_HOST = _get_conf('SAVANNA_HOST', '192.168.1.1')
SAVANNA_PORT = _get_conf('SAVANNA_PORT', '8080')

IMAGE_ID = _get_conf('IMAGE_ID', '42')
FLAVOR_ID = _get_conf('FLAVOR_ID', 'abc')

CLUSTER_NAME_CRUD = _get_conf('CLUSTER_NAME_CRUD', 'cluster-crud')
CLUSTER_NAME_HADOOP = _get_conf('CLUSTER_NAME_HADOOP', 'cluster-hadoop')

HADOOP_VERSION = _get_conf('HADOOP_VERSION', '1.1.2')

SSH_KEY = _get_conf('SSH_KEY', 'jenkins')
PLUGIN_NAME = _get_conf('PLUGIN_NAME', 'vanilla')
