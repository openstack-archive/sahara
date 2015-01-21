# Copyright (c) 2013 Hortonworks, Inc.
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

import functools
import inspect
import logging
from logging import handlers
import os
import sys
import time

from oslo.config import cfg
from oslo_log import log

from sahara.i18n import _LI


CONF = cfg.CONF
LOG = log.getLogger(__name__)


def _get_log_file_path(logfile):
    logdir = CONF.log_dir
    if not logdir:
        logdir = os.path.curdir
    return os.path.join(logdir, logfile)


fh = handlers.WatchedFileHandler(_get_log_file_path('timing.log'))
fh.setLevel(logging.DEBUG)
LOG.logger.addHandler(fh)


def timed(f):
    @functools.wraps(f)
    def wrapper(*args, **kwds):

        indent_level = len(inspect.stack()) - 1
        start = time.time()
        try:
            result = f(*args, **kwds)
        except Exception:
            LOG.info(
                _LI('Exception raised by invocation of %(name)s: %(info)s'),
                {'name': f.__name__, 'info': sys.exc_info()[0]})
            raise
        finally:
            elapsed = time.time() - start
            LOG.info('-' * indent_level + '{0}({1}), {2} seconds'.format(
                     f.__name__, args[0].__class__.__name__, elapsed))
        return result
    return wrapper
