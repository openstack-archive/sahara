# Copyright (c) 2016 Intel Corporation.
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

import uuid

import six

from sahara import conductor
from sahara import context
from sahara.service.castellan import utils as key_manager

MAPR_USER_NAME = 'mapr'
MAPR_USER_PASSWORD = 'mapr_password'

conductor = conductor.API


def delete_password(cluster, pw_name):
    """delete the named password from the key manager

    This function will lookup the named password in the cluster entry
    and delete it from the key manager.

    :param cluster: The cluster record containing the password
    :param pw_name: The name associated with the password
    """
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster.id)
    key_id = cluster.extra.get(pw_name) if cluster.extra else None
    if key_id is not None:
        key_manager.delete_key(key_id, ctx)


def get_password(cluster, pw_name):
    """return a password for the named entry

    This function will return, or create and return, a password for the
    named entry. It will store the password in the key manager and use
    the ID in the database entry.

    :param cluster: The cluster record containing the password
    :param pw_name: The entry name associated with the password
    :returns: The cleartext password
    """
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster.id)
    passwd = cluster.extra.get(pw_name) if cluster.extra else None
    if passwd:
        return key_manager.get_secret(passwd, ctx)

    passwd = six.text_type(uuid.uuid4())
    extra = cluster.extra.to_dict() if cluster.extra else {}
    extra[pw_name] = key_manager.store_secret(passwd, ctx)
    cluster = conductor.cluster_update(ctx, cluster, {'extra': extra})
    return passwd


def get_mapr_password(cluster):
    return get_password(cluster, MAPR_USER_PASSWORD)
