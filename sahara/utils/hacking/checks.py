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

import pep8

import re
import tokenize

from sahara.utils.hacking import commit_message
from sahara.utils.hacking import import_checks
from sahara.utils.hacking import logging_checks


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


def check_oslo_namespace_imports(logical_line):
    """Check to prevent old oslo namespace usage.

    S363
    """
    oslo_imports = (re.compile(r"(((from)|(import))\s+oslo\.)"),
                    re.compile(r"(from\s+oslo\s+import)"))

    if re.match(oslo_imports[0], logical_line):
        yield(0, "S363: '%s' must be used instead of '%s'." % (
            logical_line.replace('oslo.', 'oslo_'),
            logical_line))

    if re.match(oslo_imports[1], logical_line):
        yield(0, "S363: '%s' must be used instead of '%s'" % (
              'import oslo_%s' % logical_line.split()[-1],
              logical_line))


def dict_constructor_with_list_copy(logical_line):
    """Check to prevent dict constructor with a sequence of key-value pairs.

    S368
    """
    dict_constructor_with_list_copy_re = re.compile(r".*\bdict\((\[)?(\(|\[)")

    if dict_constructor_with_list_copy_re.match(logical_line):
        yield (0, 'S368: Must use a dict comprehension instead of a dict '
               'constructor with a sequence of key-value pairs.')


def use_jsonutils(logical_line, filename):
    """Check to prevent importing json in sahara code.

    S375
    """
    if pep8.noqa(logical_line):
        return
    invalid_line = re.compile(r"(import\s+json)")
    valid_line = re.compile(r"(import\s+jsonschema)")
    if (re.match(invalid_line, logical_line) and
            not re.match(valid_line, logical_line)):
        yield(0, "S375: Use jsonutils from oslo_serialization instead"
                 " of json")


def no_mutable_default_args(logical_line):
    """Check to prevent mutable default argument in sahara code.

    S360
    """
    msg = "S360: Method's default argument shouldn't be mutable!"
    mutable_default_args = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")
    if mutable_default_args.match(logical_line):
        yield (0, msg)


def factory(register):
    register(import_db_only_in_conductor)
    register(hacking_no_author_attr)
    register(check_oslo_namespace_imports)
    register(commit_message.OnceGitCheckCommitTitleBug)
    register(commit_message.OnceGitCheckCommitTitleLength)
    register(import_checks.hacking_import_groups)
    register(import_checks.hacking_import_groups_together)
    register(dict_constructor_with_list_copy)
    register(logging_checks.validate_log_translations)
    register(logging_checks.no_translate_debug_logs)
    register(logging_checks.accepted_log_levels)
    register(use_jsonutils)
    register(no_mutable_default_args)
