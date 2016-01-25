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

from sahara import exceptions as ex
from sahara.i18n import _


def check_tenant_for_delete(context, object):
    if object.tenant_id != context.tenant_id:
        raise ex.DeletionFailed(
            _("{object} with id '{id}' could not be deleted because "
              "it wasn't created in this tenant").format(
                object=type(object).__name__, id=object.id))


def check_tenant_for_update(context, object):
    if object.tenant_id != context.tenant_id:
        raise ex.UpdateFailedException(
            object.id,
            _("{object} with id '%s' could not be updated because "
              "it wasn't created in this tenant").format(
                object=type(object).__name__))


def check_protected_from_delete(object):
    if object.is_protected:
        raise ex.DeletionFailed(
            _("{object} with id '{id}' could not be deleted because "
              "it's marked as protected").format(
                object=type(object).__name__, id=object.id))


def check_protected_from_update(object, data):
    if object.is_protected and data.get('is_protected', True):
        # Okay, the only thing we can allow here is a change
        # to 'is_public', so we have to make sure no other values
        # are changing
        if 'is_public' in data:
            obj = object.to_dict()
            if all(k == 'is_public' or (
                    k in obj and obj[k] == v) for k, v in six.iteritems(data)):
                return

        raise ex.UpdateFailedException(
            object.id,
            _("{object} with id '%s' could not be updated "
              "because it's marked as protected").format(
                object=type(object).__name__))
