# Copyright (c) 2015 Mirantis Inc.
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

import bisect
import hashlib

from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils
from tooz import coordination

LOG = log.getLogger(__name__)

coordinator_opts = [
    cfg.IntOpt('coordinator_heartbeat_interval',
               default=1,
               help='Interval size between heartbeat execution in seconds. '
                    'Heartbeats are executed to make sure that connection to '
                    'the coordination server is active.'),
    cfg.IntOpt('hash_ring_replicas_count',
               default=40,
               help='Number of points that belongs to each member on a hash '
                    'ring. The larger number leads to a better distribution.')
]

CONF = cfg.CONF
CONF.register_opts(coordinator_opts)


class Coordinator(object):
    def __init__(self, backend_url):
        self.coordinator = None
        self.member_id = uuidutils.generate_uuid()

        if backend_url:
            try:
                self.coordinator = coordination.get_coordinator(
                    backend_url, self.member_id)
                self.coordinator.start()
                LOG.info('Coordination backend loaded successfully.')
            except coordination.ToozError:
                LOG.error('Error connecting to coordination backend.')
                raise

    def is_started(self):
        if self.coordinator:
            return self.coordinator.is_started
        return False

    def heartbeat(self):
        if self.coordinator:
            self.coordinator.heartbeat()

    def join_group(self, group_id):
        if self.coordinator:
            try:
                self.coordinator.join_group(group_id).get()
            except coordination.GroupNotCreated:
                try:
                    self.coordinator.create_group(group_id).get()
                except coordination.GroupAlreadyExist:
                    pass
                self.coordinator.join_group(group_id).get()

    def get_members(self, group_id):
        if self.coordinator:
            for i in range(2):
                try:
                    members = self.coordinator.get_members(group_id).get()
                    if self.member_id in members:
                        return members
                    self.join_group(group_id)
                except coordination.GroupNotCreated:
                    self.join_group(group_id)
                except coordination.ToozError as e:
                    LOG.error("Couldn't get members of {group} group. "
                              "Reason: {ex}".format(
                                  group=group_id, ex=str(e)))
        return []


class HashRing(Coordinator):
    def __init__(self, backend_url, group_id):
        self.group_id = group_id
        self.replicas = CONF.hash_ring_replicas_count
        super(HashRing, self).__init__(backend_url)
        self.join_group(group_id)

    @staticmethod
    def _hash(key):
        return int(
            hashlib.md5(str(key).encode('utf-8')).hexdigest(), 16)  # nosec

    def _build_ring(self):
        ring = {}
        members = self.get_members(self.group_id)
        for member in members:
            for r in range(self.replicas):
                hashed_key = self._hash('%s:%s' % (member, r))
                ring[hashed_key] = member

        return ring, sorted(ring.keys())

    def _check_object(self, object, ring, sorted_keys):
        """Checks if this object belongs to this member or not"""
        hashed_key = self._hash(object.id)
        position = bisect.bisect(sorted_keys, hashed_key)
        position = position if position < len(sorted_keys) else 0
        return ring[sorted_keys[position]] == self.member_id

    def get_subset(self, objects):
        """Returns subset that belongs to this member"""
        if self.coordinator:
            ring, keys = self._build_ring()
            if ring:
                return [obj for obj in objects if self._check_object(
                    obj, ring, keys)]
            return []
        return objects
