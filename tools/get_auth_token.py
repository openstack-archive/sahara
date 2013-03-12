import os.path, sys

from flask import Config
from keystoneclient.v2_0 import Client as keystone_client


def main():
    if len(sys.argv) > 1 and len(sys.argv) != 4:
      print "You must either specify no parameters or exactly 3: <username> <password> <tenant>.\n" \
            "If you specify no parameters, credentials and tenant will be taken from config"
      exit

    scriptDir = os.path.dirname(os.path.realpath(__file__))
    config = Config(scriptDir + '/../etc')
    config.from_pyfile('local.cfg')

    print "Configuration has been loaded from 'etc/local.cfg'"

    if len(sys.argv) == 4:
        user = sys.argv[1]
        password = sys.argv[2]
        tenant = sys.argv[3]
    else:
        print "You didn't provided credentials, using ones found in config"
        user = config['OS_ADMIN_USER']
        password = config['OS_ADMIN_PASSWORD']
        tenant = config['OS_ADMIN_TENANT']

    protocol = config['OS_AUTH_PROTOCOL']
    host = config['OS_AUTH_HOST']
    port = config['OS_AUTH_PORT']

    auth_url = "%s://%s:%s/v2.0/" % (protocol, host, port)

    print "User: %s" % user
    print "Password: %s" % password
    print "Tenant: %s" % tenant
    print "Auth URL: %s" % auth_url

    keystone = keystone_client(
        username=user,
        password=password,
        tenant_name=tenant,
        auth_url=auth_url
    )

    result = keystone.authenticate()

    print "Auth succeed: %s" % result
    print "Auth token: %s" % keystone.auth_token
    print "Tenant [%s] id: %s" % (tenant, keystone.tenant_id)

if __name__ == "__main__":
    main()
