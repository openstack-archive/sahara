# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

r"""
When using the global cfg.CONF object, it is quite common for a module
to require the existence of configuration options registered by other
modules.

For example, if module 'foo' registers the 'blaa' option and the module
'bar' uses the 'blaa' option then 'bar' might do:

  import foo

  print(CONF.blaa)

However, it's completely non-obvious why foo is being imported (is it
unused, can we remove the import) and where the 'blaa' option comes from.

The CONF.import_opt() method allows such a dependency to be explicitly
declared:

  CONF.import_opt('blaa', 'foo')
  print(CONF.blaa)

However, import_opt() has a weakness - if 'bar' imports 'foo' using the
import builtin and doesn't use import_opt() to import 'blaa', then 'blaa'
can still be used without problems. Similarily, where multiple options
are registered a module imported via importopt(), a lazy programmer can
get away with only declaring a dependency on a single option.

The ConfigFilter class provides a way to ensure that options are not
available unless they have been registered in the module or imported using
import_opt() e.g. with:

  CONF = ConfigFilter(cfg.CONF)
  CONF.import_opt('blaa', 'foo')
  print(CONF.blaa)

no other options other than 'blaa' are available via CONF.
"""

import collections
import itertools

from oslo.config import cfg


class ConfigFilter(collections.Mapping):

    """A helper class which wraps a ConfigOpts object.

    ConfigFilter enforces the explicit declaration of dependencies on external
    options.
    """

    def __init__(self, conf):
        """Construct a ConfigFilter object.

        :param conf: a ConfigOpts object
        """
        self._conf = conf
        self._opts = set()
        self._groups = dict()

    def __getattr__(self, name):
        """Look up an option value.

        :param name: the opt name (or 'dest', more precisely)
        :returns: the option value (after string subsititution) or a GroupAttr
        :raises: NoSuchOptError,ConfigFileValueError,TemplateSubstitutionError
        """
        if name in self._groups:
            return self._groups[name]
        if name not in self._opts:
            raise cfg.NoSuchOptError(name)
        return getattr(self._conf, name)

    def __getitem__(self, key):
        """Look up an option value."""
        return getattr(self, key)

    def __contains__(self, key):
        """Return True if key is the name of a registered opt or group."""
        return key in self._opts or key in self._groups

    def __iter__(self):
        """Iterate over all registered opt and group names."""
        return itertools.chain(self._opts, self._groups.keys())

    def __len__(self):
        """Return the number of options and option groups."""
        return len(self._opts) + len(self._groups)

    def register_opt(self, opt, group=None):
        """Register an option schema.

        :param opt: an instance of an Opt sub-class
        :param group: an optional OptGroup object or group name
        :return: False if the opt was already registered, True otherwise
        :raises: DuplicateOptError
        """
        if not self._conf.register_opt(opt, group):
            return False

        self._register_opt(opt.dest, group)
        return True

    def register_opts(self, opts, group=None):
        """Register multiple option schemas at once."""
        for opt in opts:
            self.register_opt(opt, group)

    def register_cli_opt(self, opt, group=None):
        """Register a CLI option schema.

        :param opt: an instance of an Opt sub-class
        :param group: an optional OptGroup object or group name
        :return: False if the opt was already register, True otherwise
        :raises: DuplicateOptError, ArgsAlreadyParsedError
        """
        if not self._conf.register_cli_opt(opt, group):
            return False

        self._register_opt(opt.dest, group)
        return True

    def register_cli_opts(self, opts, group=None):
        """Register multiple CLI option schemas at once."""
        for opt in opts:
            self.register_cli_opts(opt, group)

    def register_group(self, group):
        """Register an option group.

        :param group: an OptGroup object
        """
        self._conf.register_group(group)
        self._get_group(group.name)

    def import_opt(self, opt_name, module_str, group=None):
        """Import an option definition from a module.

        :param name: the name/dest of the opt
        :param module_str: the name of a module to import
        :param group: an option OptGroup object or group name
        :raises: NoSuchOptError, NoSuchGroupError
        """
        self._conf.import_opt(opt_name, module_str, group)
        self._register_opt(opt_name, group)

    def import_group(self, group, module_str):
        """Import an option group from a module.

        Note that this allows access to all options registered with
        the group whether or not those options were registered by
        the given module.

        :param group: an option OptGroup object or group name
        :param module_str: the name of a module to import
        :raises: ImportError, NoSuchGroupError
        """
        self._conf.import_group(group, module_str)
        group = self._get_group(group)
        group._all_opts = True

    def _register_opt(self, opt_name, group):
        if group is None:
            self._opts.add(opt_name)
            return True
        else:
            group = self._get_group(group)
            return group._register_opt(opt_name)

    def _get_group(self, group_or_name):
        if isinstance(group_or_name, cfg.OptGroup):
            group_name = group_or_name.name
        else:
            group_name = group_or_name

        if group_name in self._groups:
            return self._groups[group_name]
        else:
            group = self.GroupAttr(self._conf, group_name)
            self._groups[group_name] = group
            return group

    class GroupAttr(collections.Mapping):

        """Helper class to wrap a group object.

        Represents the option values of a group as a mapping and attributes.
        """

        def __init__(self, conf, group):
            """Construct a GroupAttr object.

            :param conf: a ConfigOpts object
            :param group: an OptGroup object
            """
            self._conf = conf
            self._group = group
            self._opts = set()
            self._all_opts = False

        def __getattr__(self, name):
            """Look up an option value."""
            if not self._all_opts and name not in self._opts:
                raise cfg.NoSuchOptError(name)
            return getattr(self._conf[self._group], name)

        def __getitem__(self, key):
            """Look up an option value."""
            return getattr(self, key)

        def __contains__(self, key):
            """Return True if key is the name of a registered opt or group."""
            return key in self._opts

        def __iter__(self):
            """Iterate over all registered opt and group names."""
            for key in self._opts:
                yield key

        def __len__(self):
            """Return the number of options and option groups."""
            return len(self._opts)

        def _register_opt(self, opt_name):
            self._opts.add(opt_name)
