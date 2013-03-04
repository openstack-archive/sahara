import logging
from eho.server.utils.openstack.base import url_for
from novaclient.v1_1 import client as nova_client


def novaclient(headers):
    username = headers['X-User-Name']
    token = headers['X-Auth-Token']
    tenant = headers['X-Tenant-Id']
    compute_url = url_for(headers, 'compute')

    logging.debug('novaclient connection created using token '
                  '"%s" and url "%s"', token, compute_url)

    nova = nova_client.Client(username, token, tenant,
                              auth_url=compute_url)

    nova.client.auth_token = token
    nova.client.management_url = compute_url

    return nova
