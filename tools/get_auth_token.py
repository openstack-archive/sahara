from flask import Config
from keystoneclient.v2_0 import Client as keystone_client


def main():
    config = Config('etc')
    config.from_pyfile('local.cfg')

    print "Configuration has been loaded from 'etc/local.cfg': %s" % config

    user = config['OS_ADMIN_USER']
    password = config['OS_ADMIN_PASSWORD']
    tenant = config['OS_ADMIN_TENANT']

    protocol = config['OS_AUTH_PROTOCOL']
    host = config['OS_AUTH_HOST']
    port = config['OS_AUTH_PORT']

    keystone = keystone_client(
        username=user,
        password=password,
        tenant_name=tenant,
        auth_url="%s://%s:%s/v2.0/" % (protocol, host, port)
    )

    result = keystone.authenticate()

    print "Auth result: %s" % result
    print "Auth token: %s" % keystone.auth_token


if __name__ == "__main__":
    main()
