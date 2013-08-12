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


import six


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
