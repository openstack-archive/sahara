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


from sahara.utils import cluster_progress_ops as cpo


def provision_step(name, cluster_context_reference=1, instances_reference=2):
    def wrapper(function):
        def wrapped(*args, **kwargs):
            cluster_context = _find_argument(
                cluster_context_reference, *args, **kwargs)
            instances = _find_argument(instances_reference, *args, **kwargs)

            cluster_id = cluster_context.cluster.id
            instance_count = len(instances)

            cpo.add_provisioning_step(cluster_id, name, instance_count)

            return function(*args, **kwargs)

        return wrapped

    return wrapper


def provision_event(instance_reference=0, name=None, instance=None):
    def wrapper(function):
        def wrapped(*args, **kwargs):
            event_instance = instance or _find_argument(instance_reference,
                                                        *args, **kwargs)
            if name:
                cpo.add_provisioning_step(event_instance.node_group.cluster.id,
                                          name, 1)
            try:
                result = function(*args, **kwargs)
                cpo.add_successful_event(event_instance)
                return result
            except Exception as exception:
                cpo.add_fail_event(event_instance, exception)
                raise exception

        return wrapped

    return wrapper


def _find_argument(reference, *args, **kwargs):
    if isinstance(reference, int):
        return args[reference]
    if isinstance(reference, str):
        return kwargs[reference]
