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


from sahara.service.castellan import utils as castellan_utils


def delete_secret(id, ctx=None, **kwargs):
    castellan_utils.delete_secret(id, ctx=ctx)


def get_secret(id, ctx=None, **kwargs):
    return castellan_utils.get_secret(id, ctx=ctx)


def store_secret(secret, ctx=None, **kwargs):
    return castellan_utils.store_secret(secret)
