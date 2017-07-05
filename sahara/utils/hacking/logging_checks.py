#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import re


_all_log_levels = "info|exception|warning|critical|error|debug"

_accepted_log_level = re.compile(
    r"(.)*LOG\.(%(levels)s)\(" % {'levels': _all_log_levels})

# Since _Lx() have been removed, we just need to check _()
_translated_log = re.compile(
    r"(.)*LOG\.(%(levels)s)\(\s*_\(" % {'levels': _all_log_levels})


def no_translate_logs(logical_line, filename):
    """Check for 'LOG.*(_('

    Translators don't provide translations for log messages, and operators
    asked not to translate them.

    * This check assumes that 'LOG' is a logger.
    * Use filename so we can start enforcing this in specific folders instead
      of needing to do so all at once.
    S373
    """

    msg = "S373 Don't translate logs"
    if _translated_log.match(logical_line):
        yield (0, msg)


def accepted_log_levels(logical_line, filename):
    """In Sahara we use only 5 log levels.

    This check is needed because we don't want new contributors to
    use deprecated log levels.
    S374
    """

    # NOTE(Kezar): sahara/tests included because we don't require translations
    # in tests. sahara/db/templates provide separate cli interface so we don't
    # want to translate it.

    ignore_dirs = ["sahara/db/templates",
                   "sahara/tests"]
    for directory in ignore_dirs:
        if directory in filename:
            return
    msg = ("S374 You used deprecated log level. Accepted log levels are "
           "%(levels)s" % {'levels': _all_log_levels})
    if logical_line.startswith("LOG."):
        if not _accepted_log_level.search(logical_line):
            yield(0, msg)
