# Copyright (c) 2016 Red Hat Inc.
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

import testtools

from sahara import exceptions as ex
from sahara.service.validations import acl
from sahara.tests.unit import base


class FakeObject(object):
    def __init__(self, protected, values):
        self.values = values
        self.is_protected = protected
        self.id = "fakeid"

    def to_dict(self):
        return self.values


class TestProtectedValidation(base.SaharaTestCase):
    def test_public_on_protected(self):
        prot = FakeObject(True, {"cat": 1,
                                 "dog": 2})
        values = {"cat": 3, "dog": 2}

        # Should raise because prot.is_protected is True
        with testtools.ExpectedException(ex.UpdateFailedException):
            acl.check_protected_from_update(prot, values)

        # Should not raise because values turns is_protected off
        values["is_protected"] = False
        acl.check_protected_from_update(prot, values)

        # Should be allowed because is_public is the only thing
        # that is potentially changing
        values = {"cat": 1, "dog": 2, "is_public": True}
        acl.check_protected_from_update(prot, values)

        values["cat"] = 3
        # Should raise because we are trying to change cat, too
        with testtools.ExpectedException(ex.UpdateFailedException):
            acl.check_protected_from_update(prot, values)
