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

import re

import six


NATURAL_SORT_RE = re.compile('([0-9]+)')


def find_dict(iterable, **rules):
    """Search for dict in iterable of dicts using specified key-value rules."""

    for item in iterable:
        # assert all key-value pairs from rules dict
        ok = True
        for k, v in six.iteritems(rules):
            ok = ok and k in item and item[k] == v

        if ok:
            return item

    return None


def find(lst, **kwargs):
    for obj in lst:
        match = True
        for attr, value in kwargs.items():
            if getattr(obj, attr) != value:
                match = False

        if match:
            return obj

    return None


def get_by_id(lst, id):
    for obj in lst:
        if obj.id == id:
            return obj

    return None


# Taken from http://stackoverflow.com/questions/4836710/does-
# python-have-a-built-in-function-for-string-natural-sort
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(NATURAL_SORT_RE, s)]


def generate_instance_name(cluster_name, node_group_name, index):
    return ("%s-%s-%03d" % (cluster_name, node_group_name, index)).lower()


def generate_auto_security_group_name(node_group):
    return ("%s-%s-%s" % (node_group.cluster.name, node_group.name,
                          node_group.id[:8])).lower()


def generate_aa_group_name(cluster_name, server_group_index):
    return ("%s-aa-group-%d" % (cluster_name, server_group_index)).lower()
