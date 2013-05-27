import savanna.openstack.common.importutils as importutils

_CONF = importutils.try_import('savanna.tests.integration.config')


def _get_conf(key, default):
    return getattr(_CONF, key) if _CONF and hasattr(_CONF, key) else default

OS_USERNAME = _get_conf('OS_USERNAME', 'admin')
OS_PASSWORD = _get_conf('OS_PASSWORD', 'password')
OS_TENANT_NAME = _get_conf('OS_TENANT_NAME', 'admin')
OS_AUTH_URL = _get_conf('OS_AUTH_URL', 'http://localhost:35357/v2.0/')

SAVANNA_HOST = _get_conf('SAVANNA_HOST', '192.168.1.1')
SAVANNA_PORT = _get_conf('SAVANNA_PORT', '8080')

IMAGE_ID = _get_conf('IMAGE_ID', '42')
FLAVOR_ID = _get_conf('FLAVOR_ID', 'abc')

NODE_USERNAME = _get_conf('NODE_USERNAME', 'username')
NODE_PASSWORD = _get_conf('NODE_PASSWORD', 'password')

CLUSTER_NAME_CRUD = _get_conf('CLUSTER_NAME_CRUD', 'cluster-crud')
CLUSTER_NAME_HADOOP = _get_conf('CLUSTER_NAME_HADOOP', 'cluster-hadoop')

IP_PREFIX = _get_conf('IP_PREFIX', '10.')

TIMEOUT = _get_conf('TIMEOUT', '15')

HADOOP_VERSION = _get_conf('HADOOP_VERSION', '1.1.1')
HADOOP_DIRECTORY = _get_conf('HADOOP_DIRECTORY', '/usr/share/hadoop')
HADOOP_LOG_DIRECTORY = _get_conf('HADOOP_LOG_DIRECTORY',
                                 '/mnt/log/hadoop/hadoop/userlogs')
