# Copyright (c) 2018 Red Hat, Inc.
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

from sahara import conductor

conductor = conductor.API


def cluster_get(context, cluster_id, **kwargs):
    return conductor.cluster_get(context, cluster_id)


def cluster_update(context, cluster, values, **kwargs):
    return conductor.cluster_update(context, cluster, values)


def cluster_create(context, values, **kwargs):
    return conductor.cluster_create(context, values)


def plugin_create(context, values, **kwargs):
    return conductor.plugin_create(context, values)


def plugin_remove(context, name, **kwargs):
    return conductor.plugin_remove(context, name)
