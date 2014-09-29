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


import tokenize


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
               "sahara/conductor",
               "sahara/tests",
               "sahara/db"):
        return

    if _starts_with_any(logical_line,
                        "from sahara import db",
                        "from sahara.db",
                        "import sahara.db"):
        yield (0, "S361: sahara.db import only allowed in "
                  "sahara/conductor/*")


def hacking_no_author_attr(logical_line, tokens):
    """__author__ should not be used.

    S362: __author__ = slukjanov
    """
    for token_type, text, start_index, _, _ in tokens:
        if token_type == tokenize.NAME and text == "__author__":
            yield (start_index[1],
                   "S362: __author__ should not be used")


def factory(register):
    register(import_db_only_in_conductor)
    register(hacking_no_author_attr)
