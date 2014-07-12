# Copyright (c) 2014 Mirantis Inc.
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

# It's based on oslo.i18n usage in OpenStack Keystone project and
# recommendations from http://docs.openstack.org/developer/oslo.i18n/usage.html

from oslo import i18n


_translators = i18n.TranslatorFactory(domain='sahara')

# The primary translation function using the well-known name "_"
_ = _translators.primary

# Translators for log levels.
#
# The abbreviated names are meant to reflect the usual use of a short
# name like '_'. The "L" is for "log" and the other letter comes from
# the level.
_LI = _translators.log_info
_LW = _translators.log_warning
_LE = _translators.log_error
_LC = _translators.log_critical


# Due to the fact that some modules in oslo-incubator synced to the
# sahara/openstack/common are using its own gettextutils we're monkey patching
# our copy of oslo-incubator's gettextutils to use our initialized oslo.i18n
# versions.

# FIXME(slukjanov): Remove the monkey patch when oslo-incubator will fully use
#                   oslo.i18n and this code will be synced to sahara. The
#                   sahara/openstack/common/gettextutils.py after that

from sahara.openstack.common import gettextutils


gettextutils._ = _
gettextutils._LI = _LI
gettextutils._LW = _LW
gettextutils._LE = _LE
gettextutils._LC = _LC
