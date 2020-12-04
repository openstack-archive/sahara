# Copyright (c) 2017 OpenStack Foundation
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


from oslo_config import cfg
from oslo_log import log as logging
import six
import six.moves.urllib.parse as urlparse
from stevedore import enabled

from sahara import conductor as cond
from sahara import exceptions as ex
from sahara.i18n import _

conductor = cond.API

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class JobBinaryManager(object):
    def __init__(self):
        self.job_binaries = {}
        self._load_job_binaries()

    def _load_job_binaries(self):
        config_jb = CONF.job_binary_types
        extension_manager = enabled.EnabledExtensionManager(
            check_func=lambda ext: ext.name in config_jb,
            namespace='sahara.job_binary.types',
            invoke_on_load=True
        )

        for ext in extension_manager.extensions:
            if ext.name in self.job_binaries:
                raise ex.ConfigurationError(
                    _("Job binary with name '%s' already exists.") %
                    ext.name)
            ext.obj.name = ext.name
            self.job_binaries[ext.name] = ext.obj
            LOG.info("Job binary name {jb_name} loaded {entry_point}".format(
                jb_name=ext.name, entry_point=ext.entry_point_target))

        if len(self.job_binaries) < len(config_jb):
            loaded_jb = set(six.iterkeys(self.job_binaries))
            requested_jb = set(config_jb)
            raise ex.ConfigurationError(
                _("Job binaries couldn't be loaded: %s") %
                ", ".join(requested_jb - loaded_jb))

    def get_job_binaries(self):
        config_jb = CONF.job_binary_types
        return [self.get_job_binary(name).name for name in config_jb]

    def get_job_binary(self, name):
        res = self.job_binaries.get(name)
        if res is None:
            raise ex.InvalidDataException(_("Invalid job binary"))
        return res

    def get_job_binary_by_url(self, url):
        url = urlparse.urlparse(url)
        if not url.scheme:
            raise ex.InvalidDataException(
                _("Job binary url must have a scheme"))
        return self.get_job_binary(url.scheme)


JOB_BINARIES = None


def setup_job_binaries():
    global JOB_BINARIES
    JOB_BINARIES = JobBinaryManager()
