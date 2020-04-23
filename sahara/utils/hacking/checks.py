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

import pycodestyle

import re
import tokenize

from hacking import core


RE_OSLO_IMPORTS = (re.compile(r"(((from)|(import))\s+oslo\.)"),
                   re.compile(r"(from\s+oslo\s+import)"))
RE_DICT_CONSTRUCTOR_WITH_LIST_COPY = re.compile(r".*\bdict\((\[)?(\(|\[)")
RE_USE_JSONUTILS_INVALID_LINE = re.compile(r"(import\s+json)")
RE_USE_JSONUTILS_VALID_LINE = re.compile(r"(import\s+jsonschema)")
RE_MUTABLE_DEFAULT_ARGS = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")


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


@core.flake8ext
def import_db_only_in_conductor(logical_line, filename):
    """Check that db calls are only in conductor, plugins module and in tests.

    S361
    """
    if _any_in(filename,
               "sahara/conductor",
               "sahara/plugins",
               "sahara/tests",
               "sahara/db"):
        return

    if _starts_with_any(logical_line,
                        "from sahara import db",
                        "from sahara.db",
                        "import sahara.db"):
        yield (0, "S361: sahara.db import only allowed in "
                  "sahara/conductor/*")


@core.flake8ext
def hacking_no_author_attr(logical_line, tokens):
    """__author__ should not be used.

    S362: __author__ = slukjanov
    """
    for token_type, text, start_index, _, _ in tokens:
        if token_type == tokenize.NAME and text == "__author__":
            yield (start_index[1],
                   "S362: __author__ should not be used")


@core.flake8ext
def check_oslo_namespace_imports(logical_line):
    """Check to prevent old oslo namespace usage.

    S363
    """
    if re.match(RE_OSLO_IMPORTS[0], logical_line):
        yield(0, "S363: '%s' must be used instead of '%s'." % (
            logical_line.replace('oslo.', 'oslo_'),
            logical_line))

    if re.match(RE_OSLO_IMPORTS[1], logical_line):
        yield(0, "S363: '%s' must be used instead of '%s'" % (
              'import oslo_%s' % logical_line.split()[-1],
              logical_line))


@core.flake8ext
def dict_constructor_with_list_copy(logical_line):
    """Check to prevent dict constructor with a sequence of key-value pairs.

    S368
    """
    if RE_DICT_CONSTRUCTOR_WITH_LIST_COPY.match(logical_line):
        yield (0, 'S368: Must use a dict comprehension instead of a dict '
                  'constructor with a sequence of key-value pairs.')


@core.flake8ext
def use_jsonutils(logical_line, filename):
    """Check to prevent importing json in sahara code.

    S375
    """
    if pycodestyle.noqa(logical_line):
        return
    if (RE_USE_JSONUTILS_INVALID_LINE.match(logical_line) and
            not RE_USE_JSONUTILS_VALID_LINE.match(logical_line)):
        yield(0, "S375: Use jsonutils from oslo_serialization instead"
                 " of json")


@core.flake8ext
def no_mutable_default_args(logical_line):
    """Check to prevent mutable default argument in sahara code.

    S360
    """
    msg = "S360: Method's default argument shouldn't be mutable!"
    if RE_MUTABLE_DEFAULT_ARGS.match(logical_line):
        yield (0, msg)
