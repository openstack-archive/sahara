# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import oslo_serialization.jsonutils as json

from sahara.i18n import _
import sahara.plugins.mapr.util.general as util
from sahara.utils import poll_utils as polls


WARDEN_MANAGED_CMD = ('sudo -u mapr maprcli node services'
                      ' -name %(service)s'
                      ' -action %(action)s'
                      ' -nodes %(nodes)s')


class NodeProcess(object):
    def __init__(self, name, ui_name, package, open_ports=None):
        self._name = name
        self._ui_name = ui_name
        self._package = package
        self._open_ports = open_ports or []

    @property
    def name(self):
        return self._name

    @property
    def ui_name(self):
        return self._ui_name

    @property
    def package(self):
        return self._package

    @property
    def open_ports(self):
        return self._open_ports

    def start(self, instances):
        self.execute_action(instances, Action.START)

    def restart(self, instances):
        self.execute_action(instances, Action.RESTART)

    def stop(self, instances):
        self.execute_action(instances, Action.STOP)

    def execute_action(self, instances, action):
        if len(instances) == 0:
            return
        nodes = ','.join(map(lambda i: i.internal_ip, instances))
        args = {'service': self.name, 'action': action.name, 'nodes': nodes}
        command = WARDEN_MANAGED_CMD % args
        with instances[0].remote() as r:
            r.execute_command(command)
        self._wait_for_status(instances, action.status)

    def _wait_for_status(self, instances, status, sleep=3, timeout=60):
        def poll_status(instance):
            operation_name = _('Wait for {node_process} on {instance}'
                               ' to change status to "{status}"')
            args = {
                'node_process': self.ui_name,
                'instance': instance.instance_name,
                'status': status.name,
            }
            return polls.poll(
                get_status=lambda: self.status(instance) == status,
                operation_name=operation_name.format(**args),
                timeout=timeout,
                sleep=sleep,
            )

        util.execute_on_instances(instances, poll_status)

    def status(self, instance):
        command = 'maprcli service list -node %s -json' % instance.internal_ip
        with instance.remote() as remote:
            ec, out = remote.execute_command(util._run_as('mapr', command))
        node_processes = json.loads(out)['data']
        for node_process in node_processes:
            if node_process['name'] == self.name:
                return Status.by_value(node_process['state'])

        return Status.NOT_CONFIGURED

    def is_started(self, instance):
        # At least tried to do it =)
        return self.status(instance) in [Status.RUNNING,
                                         Status.FAILED,
                                         Status.STAND_BY]


class Status(object):
    class Item(object):
        def __init__(self, name, value):
            self._name = name
            self._value = value

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._value

    # The package for the service is not installed and/or
    # the service is not configured (configure.sh has not run)
    NOT_CONFIGURED = Item('Not Configured', 0)

    # The package for the service is installed and configured
    CONFIGURED = Item('Configured', 1)

    # The service is installed, started by the warden, and is currently running
    RUNNING = Item('Running', 2)

    # The service is installed and configure.sh has run,
    # but the service is not running
    STOPPED = Item('Stopped', 3)

    # The service is installed and configured, but not running
    FAILED = Item('Failed', 4)

    # The service is installed and is in standby mode, waiting to take over
    # in case of failure of another instance.
    # Mainly used for JobTracker warm standby
    STAND_BY = Item('Standby', 5)

    @staticmethod
    def items():
        return [
            Status.NOT_CONFIGURED,
            Status.CONFIGURED,
            Status.RUNNING,
            Status.STOPPED,
            Status.FAILED,
            Status.STAND_BY,
        ]

    @staticmethod
    def by_value(value):
        for v in Status.items():
            if v.value == value:
                return v


class Action(object):
    class Item(object):
        def __init__(self, name, status):
            self._name = name
            self._status = status

        @property
        def name(self):
            return self._name

        @property
        def status(self):
            return self._status

    START = Item('start', Status.RUNNING)
    STOP = Item('stop', Status.STOPPED)
    RESTART = Item('restart', Status.RUNNING)
