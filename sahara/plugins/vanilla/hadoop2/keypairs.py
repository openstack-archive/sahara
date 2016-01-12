# Copyright (c) 2016 Mirantis Inc.
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

from castellan.common.objects import passphrase
from castellan import key_manager
from oslo_log import log as logging


from sahara import conductor
from sahara import context
from sahara.utils import cluster as utils
from sahara.utils import crypto

cond = conductor.API
LOG = logging.getLogger(__name__)


def _provision_key(instance, keypair):
    def append_to(remote, file, *args, **kwargs):
        kwargs['run_as_root'] = True
        path = "/home/hadoop/.ssh/%s" % file
        remote.append_to_file(path, *args, **kwargs)
    public, private = keypair['public'], keypair['private']
    folder = '/home/hadoop/.ssh'
    with context.set_current_instance_id(instance_id=instance.instance_id):
        with instance.remote() as r:
            r.execute_command('sudo mkdir -p %s' % folder)
            append_to(r, 'authorized_keys', public)
            append_to(r, 'id_rsa', private)
            append_to(r, 'id_rsa.pub', public)
            r.execute_command('sudo chown -R hadoop %s' % folder)
            r.execute_command("sudo chmod 600 %s/id_rsa" % folder)
        LOG.debug("Passwordless ssh enabled")


def _get_secret(secret):
    key = key_manager.API().get(context.current(), secret)
    return key.get_encoded()


def _store_secret(secret):
    key = passphrase.Passphrase(secret)
    password = key_manager.API().store(context.current(), key)
    return password


def _remove_secret(secret):
    key_manager.API().delete(context.current(), secret)


def provision_keypairs(cluster, instances=None):
    extra = cluster.extra.to_dict() if cluster.extra else {}
    # use same keypair for scaling
    keypair = extra.get('vanilla_keypair')
    if not instances:
        instances = utils.get_instances(cluster)
    else:
        # scaling
        if not keypair:
            # cluster created before mitaka, skipping provisioning
            return
    if not keypair:
        private, public = crypto.generate_key_pair()
        keypair = {'public': public, 'private': private}
        extra['vanilla_keypair'] = keypair
        extra['vanilla_keypair']['private'] = _store_secret(
            keypair['private'])
        cond.cluster_update(context.ctx(), cluster, {'extra': extra})
    else:
        keypair['private'] = _get_secret(keypair['private'])
    with context.ThreadGroup() as tg:
        for instance in instances:
            tg.spawn(
                'provision-key-%s' % instance.instance_name,
                _provision_key, instance, keypair)


def drop_key(cluster):
    extra = cluster.extra.to_dict() if cluster.extra else {}
    keypair = extra.get('vanilla_keypair')
    if keypair:
        _remove_secret(keypair['private'])
