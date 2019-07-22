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

import eventlet


EVENTLET_MONKEY_PATCH_MODULES = dict(os=True,
                                     select=True,
                                     socket=True,
                                     thread=True,
                                     time=True)


def patch_all():
    """Apply all patches.

    List of patches:

    * eventlet's monkey patch for all cases;
    """
    eventlet_monkey_patch()


def eventlet_monkey_patch():
    """Apply eventlet's monkey patch.

    This call should be the first call in application. It's safe to call
    monkey_patch multiple times.
    """
    eventlet.monkey_patch(**EVENTLET_MONKEY_PATCH_MODULES)


def eventlet_import_monkey_patched(module):
    """Returns module monkey patched by eventlet.

    It's needed for some tests, for example, context test.
    """
    return eventlet.import_patched(module, **EVENTLET_MONKEY_PATCH_MODULES)
