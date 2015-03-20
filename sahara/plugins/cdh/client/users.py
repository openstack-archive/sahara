# Copyright (c) 2015 Intel Corporation.
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
#
# The contents of this file are mainly copied from cm_api sources,
# released by Cloudrea. Codes not used by Sahara CDH plugin are removed.
# You can find the original codes at
#
#     https://github.com/cloudera/cm_api/tree/master/python/src/cm_api
#
# To satisfy the pep8 and python3 tests, we did some changes to the codes.
# We also change some importings to use Sahara inherited classes.

from sahara.plugins.cdh.client import types

USERS_PATH = "/users"


def get_user(resource_root, username):
    """Look up a user by username.

    @param resource_root: The root Resource object
    @param username: Username to look up
    @return: An ApiUser object
    """
    return types.call(resource_root.get,
                      '%s/%s' % (USERS_PATH, username), ApiUser)


def update_user(resource_root, user):
    """Update a user.

    Replaces the user's details with those provided.

    @param resource_root: The root Resource object
    @param user: An ApiUser object
    @return: An ApiUser object
    """
    return types.call(resource_root.put,
                      '%s/%s' % (USERS_PATH, user.name), ApiUser, data=user)


class ApiUser(types.BaseApiResource):
    _ATTRIBUTES = {
        'name': None,
        'password': None,
        'roles': None,
    }

    def __init__(self, resource_root, name=None, password=None, roles=None):
        types.BaseApiObject.init(self, resource_root, locals())
