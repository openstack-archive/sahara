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

import os
import tempfile
import unittest
import uuid

import eventlet
from oslo.config import cfg

import savanna.main
from savanna.openstack.common import log as logging
from savanna.service import api
from savanna.storage.db import DB
from savanna.storage.defaults import setup_defaults
from savanna.storage.models import Node, NodeTemplate
from savanna.utils.openstack import nova
from savanna.utils import scheduler

LOG = logging.getLogger(__name__)


def _stub_vm_creation_job(template_id):
    template = NodeTemplate.query.filter_by(id=template_id).first()
    eventlet.sleep(2)
    return 'ip-address', uuid.uuid4().hex, template.id


def _stub_launch_cluster(headers, cluster):
    LOG.debug('stub launch_cluster called with %s, %s', headers, cluster)
    pile = eventlet.GreenPile(scheduler.POOL)

    for elem in cluster.node_counts:
        node_count = elem.count
        for _ in xrange(0, node_count):
            pile.spawn(_stub_vm_creation_job, elem.node_template_id)

    for (ip, vm_id, elem) in pile:
        DB.session.add(Node(vm_id, cluster.id, elem))
        LOG.debug("VM '%s/%s/%s' created", ip, vm_id, elem)


def _stub_stop_cluster(headers, cluster):
    LOG.debug("stub stop_cluster called with %s, %s", headers, cluster)


def _stub_auth_token(*args, **kwargs):
    LOG.debug('stub token filter called with %s, %s', args, kwargs)

    def _filter(app):
        def _handler(env, start_response):
            env['HTTP_X_TENANT_ID'] = 'tenant-id-1'
            return app(env, start_response)

        return _handler

    return _filter


def _stub_auth_valid(*args, **kwargs):
    LOG.debug('stub token validation called with %s, %s', args, kwargs)

    def _filter(app):
        def _handler(env, start_response):
            return app(env, start_response)

        return _handler

    return _filter


def _stub_get_flavors(headers):
    LOG.debug('Stub get_flavors called with %s', headers)
    return [u'test_flavor', u'test_flavor_2']


def _stub_get_images(headers):
    LOG.debug('Stub get_images called with %s', headers)
    return [u'base-image-id', u'base-image-id_2']


def _stub_get_limits(headers):
    limits = dict(maxTotalCores=100,
                  maxTotalRAMSize=51200,
                  maxTotalInstances=100,
                  totalCoresUsed=0,
                  totalRAMUsed=0,
                  totalInstancesUsed=0)

    LOG.debug('Stub get_limits called with headers %s and limits %s',
              headers, limits)

    return limits


class StubFlavor:
    def __init__(self, name, vcpus, ram):
        self.name = name
        self.vcpus = int(vcpus)
        self.ram = int(ram)


def _stub_get_flavor(headers, **kwargs):
    return StubFlavor('test_flavor', 1, 512)

CONF = cfg.CONF
CONF.import_opt('debug', 'savanna.openstack.common.log')
CONF.import_opt('allow_cluster_ops', 'savanna.config')
CONF.import_opt('database_uri', 'savanna.storage.db', group='sqlalchemy')
CONF.import_opt('echo', 'savanna.storage.db', group='sqlalchemy')


class SavannaTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.maxDiff = 10000

        # override configs
        CONF.set_override('debug', True)
        CONF.set_override('allow_cluster_ops', True)  # stub process
        CONF.set_override('database_uri', 'sqlite:///' + self.db_path,
                          group='sqlalchemy')
        CONF.set_override('echo', False, group='sqlalchemy')

        # store functions that will be stubbed
        self._prev_auth_token = savanna.main.auth_token
        self._prev_auth_valid = savanna.main.auth_valid
        self._prev_cluster_launch = api.cluster_ops.launch_cluster
        self._prev_cluster_stop = api.cluster_ops.stop_cluster
        self._prev_get_flavors = nova.get_flavors
        self._prev_get_images = nova.get_images
        self._prev_get_limits = nova.get_limits
        self._prev_get_flavor = nova.get_flavor

        # stub functions
        savanna.main.auth_token = _stub_auth_token
        savanna.main.auth_valid = _stub_auth_valid
        api.cluster_ops.launch_cluster = _stub_launch_cluster
        api.cluster_ops.stop_cluster = _stub_stop_cluster
        nova.get_flavors = _stub_get_flavors
        nova.get_images = _stub_get_images
        nova.get_limits = _stub_get_limits
        nova.get_flavor = _stub_get_flavor

        app = savanna.main.make_app()

        DB.drop_all()
        DB.create_all()
        setup_defaults(True, True)

        LOG.debug('Test db path: %s', self.db_path)
        LOG.debug('Test app.config: %s', app.config)

        self.app = app.test_client()

    def tearDown(self):
        # unstub functions
        savanna.main.auth_token = self._prev_auth_token
        savanna.main.auth_valid = self._prev_auth_valid
        api.cluster_ops.launch_cluster = self._prev_cluster_launch
        api.cluster_ops.stop_cluster = self._prev_cluster_stop
        nova.get_flavors = self._prev_get_flavors
        nova.get_images = self._prev_get_images
        nova.get_limits = self._prev_get_limits
        nova.get_flavor = self._prev_get_flavor

        os.close(self.db_fd)
        os.unlink(self.db_path)
