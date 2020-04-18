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

import jsonschema.exceptions as json_exc
import testtools
from unittest import mock

from sahara import conductor as cond
from sahara import context
from sahara import exceptions as ex
from sahara.plugins import base
from sahara.tests.unit import base as unit_base
from sahara.utils import api_validator

conductor = cond.API

EXPECTED_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "plugin_labels": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "hidden": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {
                            "type": "boolean"
                        }
                    }
                },
                "stable": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {
                            "type": "boolean"
                        }
                    }
                },
                "enabled": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {
                            "type": "boolean"
                        }
                    }
                },
                "deprecated": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "status": {
                            "type": "boolean"
                        }
                    }
                }
            }
        },
        "version_labels": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "0.1": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "hidden": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "status": {
                                    "type": "boolean"
                                }
                            }
                        },
                        "stable": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "status": {
                                    "type": "boolean"
                                }
                            }
                        },
                        "enabled": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "status": {
                                    "type": "boolean"
                                }
                            }
                        },
                        "deprecated": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "status": {
                                    "type": "boolean"
                                }
                            }
                        }
                    }
                }
            }
        },
    }
}


class TestPluginLabels(unit_base.SaharaWithDbTestCase):
    def test_validate_default_labels_load(self):
        self.override_config('plugins', 'fake')
        manager = base.PluginManager()
        for plugin in ['fake']:
            data = manager.label_handler.get_label_details(plugin)
            self.assertIsNotNone(data)
            # order doesn't play a role
            self.assertIsNotNone(data['plugin_labels'])
            self.assertEqual(
                sorted(list(manager.get_plugin(plugin).get_versions())),
                sorted(list(data.get('version_labels').keys())))

    def test_get_label_full_details(self):
        self.override_config('plugins', ['fake'])
        lh = base.PluginManager().label_handler

        result = lh.get_label_full_details('fake')
        self.assertIsNotNone(result.get('plugin_labels'))
        self.assertIsNotNone(result.get('version_labels'))
        pl = result.get('plugin_labels')

        self.assertEqual(
            ['enabled', 'hidden'],
            sorted(list(pl.keys()))
        )
        for lb in ['hidden', 'enabled']:
            self.assertEqual(
                ['description', 'mutable', 'status'],
                sorted(list(pl[lb]))
            )
        vl = result.get('version_labels')
        self.assertEqual(['0.1'], list(vl.keys()))
        vl = vl.get('0.1')

        self.assertEqual(
            ['enabled'], list(vl.keys()))

        self.assertEqual(
            ['description', 'mutable', 'status'],
            sorted(list(vl['enabled']))
        )

    def test_validate_plugin_update(self):
        def validate(plugin_name, values, validator, lh):
            validator.validate(values)
            lh.validate_plugin_update(plugin_name, values)

        values = {'plugin_labels': {'enabled': {'status': False}}}
        self.override_config('plugins', ['fake'])
        lh = base.PluginManager()
        validator = api_validator.ApiValidator(
            lh.get_plugin_update_validation_jsonschema())
        validate('fake', values, validator, lh)
        values = {'plugin_labels': {'not_exists': {'status': False}}}

        with testtools.ExpectedException(json_exc.ValidationError):
            validate('fake', values, validator, lh)

        values = {'plugin_labels': {'enabled': {'status': 'False'}}}
        with testtools.ExpectedException(json_exc.ValidationError):
            validate('fake', values, validator, lh)

        values = {'field': {'blala': 'blalalalalala'}}

        with testtools.ExpectedException(json_exc.ValidationError):
            validate('fake', values, validator, lh)

        values = {'version_labels': {'0.1': {'enabled': {'status': False}}}}
        validate('fake', values, validator, lh)

        values = {'version_labels': {'0.1': {'hidden': {'status': True}}}}
        with testtools.ExpectedException(ex.InvalidDataException):
            validate('fake', values, validator, lh)

    def test_jsonschema(self):
        self.override_config('plugins', ['fake'])
        lh = base.PluginManager()
        schema = lh.get_plugin_update_validation_jsonschema()
        self.assertEqual(EXPECTED_SCHEMA, schema)

    def test_update(self):
        self.override_config('plugins', ['fake'])
        lh = base.PluginManager()

        data = lh.update_plugin('fake', values={
            'plugin_labels': {'enabled': {'status': False}}}).dict

        # enabled is updated, but hidden still same
        self.assertFalse(data['plugin_labels']['enabled']['status'])
        self.assertTrue(data['plugin_labels']['hidden']['status'])

        data = lh.update_plugin('fake', values={
            'version_labels': {'0.1': {'enabled': {'status': False}}}}).dict

        self.assertFalse(data['plugin_labels']['enabled']['status'])
        self.assertTrue(data['plugin_labels']['hidden']['status'])
        self.assertFalse(data['version_labels']['0.1']['enabled']['status'])

    @mock.patch('sahara.plugins.labels.LOG.warning')
    def test_validate_plugin_labels(self, logger):
        self.override_config('plugins', ['fake'])
        lh = base.PluginManager()

        lh.validate_plugin_labels('fake', '0.1')
        self.assertEqual(0, logger.call_count)

        dct = {
            'name': 'fake',
            'version_labels': {
                '0.1': {
                    'deprecated': {'status': True},
                    'enabled': {'status': True}
                }
            },
            'plugin_labels': {
                'deprecated': {'status': True},
                'enabled': {'status': True}
            }
        }

        conductor.plugin_create(context.ctx(), dct)
        lh.validate_plugin_labels('fake', '0.1')
        self.assertEqual(2, logger.call_count)

        conductor.plugin_remove(context.ctx(), 'fake')
        dct['plugin_labels']['enabled']['status'] = False
        conductor.plugin_create(context.ctx(), dct)
        with testtools.ExpectedException(ex.InvalidReferenceException):
            lh.validate_plugin_labels('fake', '0.1')

        conductor.plugin_remove(context.ctx(), 'fake')
        dct['plugin_labels']['enabled']['status'] = True
        dct['version_labels']['0.1']['enabled']['status'] = False
        conductor.plugin_create(context.ctx(), dct)
        with testtools.ExpectedException(ex.InvalidReferenceException):
            lh.validate_plugin_labels('fake', '0.1')
