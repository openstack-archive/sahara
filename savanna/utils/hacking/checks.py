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


def _starts_with_any(line, *prefixes):
    for prefix in prefixes:
        if line.startswith(prefix):
            return True
    return False


def _any_in(line, *sublines):
    for subline in sublines:
        if subline in line:
            return True
    return False


def import_db_only_in_conductor(logical_line, filename):
    """Check that db calls are only in conductor module and in tests.

    S361
    """
    if _any_in(filename,
               "savanna/conductor",
               "savanna/tests",
               "savanna/db",
               # TODO(slukjanov): remove this when we'll use new db abstraction
               "savanna/db_new"):
        return

    if _starts_with_any(logical_line,
                        "from savanna import db",
                        "from savanna.db",
                        "import savanna.db"):
        yield (0, "S361: savanna.db import only allowed in "
                  "savanna/conductor/*")


def factory(register):
    register(import_db_only_in_conductor)
