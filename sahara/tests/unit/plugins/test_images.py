# Copyright (c) 2016 Red Hat, Inc.
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

from unittest import mock

from oslo_utils import uuidutils
import yaml

from sahara import exceptions as ex
from sahara.plugins import exceptions as p_ex
from sahara.plugins import images
from sahara.tests.unit import base as b


class TestImages(b.SaharaTestCase):

    def test_package_spec(self):
        cls = images.SaharaPackageValidator

        validator = cls.from_spec("java", {}, [])
        self.assertIsInstance(validator, cls)
        self.assertEqual(str(validator.packages[0]), "java")

        validator = cls.from_spec({"java": {"version": "8"}}, {}, [])
        self.assertIsInstance(validator, cls)
        self.assertEqual(str(validator.packages[0]), "java-8")

        validator = cls.from_spec(
            [{"java": {"version": "8"}}, "hadoop"], {}, [])
        self.assertIsInstance(validator, cls)
        self.assertEqual(str(validator.packages[0]), "java-8")
        self.assertEqual(str(validator.packages[1]), "hadoop")

    def test_script_spec(self):
        cls = images.SaharaScriptValidator
        resource_roots = ['tests/unit/plugins']

        validator = cls.from_spec('test_images.py', {}, resource_roots)
        self.assertIsInstance(validator, cls)
        self.assertEqual(validator.env_vars, ['test_only', 'distro'])

        validator = cls.from_spec(
            {'test_images.py': {'env_vars': ['extra-file', 'user']}},
            {}, resource_roots)
        self.assertIsInstance(validator, cls)
        self.assertEqual(validator.env_vars,
                         ['test_only', 'distro',
                          'extra-file', 'user'])

    def test_all_spec(self):
        cls = images.SaharaAllValidator
        validator_map = images.SaharaImageValidatorBase.get_validator_map()

        validator = cls.from_spec(
            [{'package': {'java': {'version': '8'}}}, {'package': 'hadoop'}],
            validator_map, [])
        self.assertIsInstance(validator, cls)
        self.assertEqual(len(validator.validators), 2)
        self.assertEqual(validator.validators[0].packages[0].name, 'java')
        self.assertEqual(validator.validators[1].packages[0].name, 'hadoop')

    def test_any_spec(self):
        cls = images.SaharaAnyValidator
        validator_map = images.SaharaImageValidatorBase.get_validator_map()

        validator = cls.from_spec(
            [{'package': {'java': {'version': '8'}}}, {'package': 'hadoop'}],
            validator_map, [])
        self.assertIsInstance(validator, cls)
        self.assertEqual(len(validator.validators), 2)
        self.assertEqual(validator.validators[0].packages[0].name, 'java')
        self.assertEqual(validator.validators[1].packages[0].name, 'hadoop')

    def test_os_case_spec(self):
        cls = images.SaharaOSCaseValidator
        validator_map = images.SaharaImageValidatorBase.get_validator_map()
        spec = [
            {'redhat': [{'package': 'nfs-utils'}]},
            {'debian': [{'package': 'nfs-common'}]}
        ]

        validator = cls.from_spec(spec, validator_map, [])
        self.assertIsInstance(validator, cls)
        self.assertEqual(len(validator.distros), 2)
        self.assertEqual(validator.distros[0].distro, 'redhat')
        self.assertEqual(validator.distros[1].distro, 'debian')
        redhat, debian = (
            validator.distros[os].validator.validators[0].packages[0].name
            for os in range(2))
        self.assertEqual(redhat, 'nfs-utils')
        self.assertEqual(debian, 'nfs-common')

    def test_sahara_image_validator_spec(self):
        cls = images.SaharaImageValidator
        validator_map = images.SaharaImageValidatorBase.get_validator_map()
        resource_roots = ['tests/unit/plugins']

        spec = """
            arguments:
              java-version:
                description: The version of java.
                default: openjdk
                required: false
                choices:
                  - openjdk
                  - oracle-java

            validators:
              - os_case:
                  - redhat:
                      - package: nfs-utils
                  - debian:
                      - package: nfs-common
              - any:
                - all:
                  - package: java-1.8.0-openjdk-devel
                  - argument_set:
                      argument_name: java-version
                      value: 1.8.0
                - all:
                  - package: java-1.7.0-openjdk-devel
                  - argument_set:
                      argument_name: java-version
                      value: 1.7.0
              - script: test_images.py
              - package:
                - hadoop
                - hadoop-libhdfs
                - hadoop-native
                - hadoop-pipes
                - hadoop-sbin
                - hadoop-lzo
                - lzo
                - lzo-devel
                - hadoop-lzo-native
              - argument_case:
                  argument_name: JAVA_VERSION
                  cases:
                    1.7.0:
                      - script: test_images.py
                    1.8.0:
                      - script: test_images.py

        """
        spec = yaml.safe_load(spec)

        validator = cls.from_spec(spec, validator_map, resource_roots)
        validators = validator.validators

        self.assertIsInstance(validator, cls)
        self.assertEqual(len(validators), 5)
        self.assertIsInstance(validators[0], images.SaharaOSCaseValidator)
        self.assertIsInstance(validators[1], images.SaharaAnyValidator)
        self.assertIsInstance(validators[2], images.SaharaScriptValidator)
        self.assertIsInstance(validators[3], images.SaharaPackageValidator)
        self.assertIsInstance(
            validators[4], images.SaharaArgumentCaseValidator)
        self.assertEqual(1, len(validator.arguments))
        self.assertEqual(validator.arguments['java-version'].required, False)
        self.assertEqual(validator.arguments['java-version'].default,
                         'openjdk')
        self.assertEqual(validator.arguments['java-version'].description,
                         'The version of java.')
        self.assertEqual(validator.arguments['java-version'].choices,
                         ['openjdk', 'oracle-java'])

    def test_package_validator_redhat(self):
        cls = images.SaharaPackageValidator
        image_arguments = {"distro": 'centos'}

        packages = [cls.Package("java", "8")]
        validator = images.SaharaPackageValidator(packages)
        remote = mock.Mock()
        validator.validate(remote, test_only=True,
                           image_arguments=image_arguments)
        remote.execute_command.assert_called_with(
            "rpm -q java-8", run_as_root=True)

        image_arguments = {"distro": 'fedora'}
        packages = [cls.Package("java", "8"), cls.Package("hadoop")]
        validator = images.SaharaPackageValidator(packages)
        remote = mock.Mock()
        remote.execute_command.side_effect = (
            ex.RemoteCommandException("So bad!"))
        try:
            validator.validate(remote, test_only=True,
                               image_arguments=image_arguments)
        except p_ex.ImageValidationError as e:
            self.assertIn("So bad!", e.message)
        remote.execute_command.assert_called_with(
            "rpm -q java-8 hadoop", run_as_root=True)
        self.assertEqual(remote.execute_command.call_count, 1)

        image_arguments = {"distro": 'redhat'}
        packages = [cls.Package("java", "8"), cls.Package("hadoop")]
        validator = images.SaharaPackageValidator(packages)
        remote = mock.Mock()

        def side_effect(call, run_as_root=False):
            if "rpm" in call:
                raise ex.RemoteCommandException("So bad!")

        remote.execute_command.side_effect = side_effect
        try:
            validator.validate(remote, test_only=False,
                               image_arguments=image_arguments)
        except p_ex.ImageValidationError as e:
            self.assertIn("So bad!", e.message)
        self.assertEqual(remote.execute_command.call_count, 3)
        calls = [mock.call("rpm -q java-8 hadoop", run_as_root=True),
                 mock.call("yum install -y java-8 hadoop", run_as_root=True),
                 mock.call("rpm -q java-8 hadoop", run_as_root=True)]
        remote.execute_command.assert_has_calls(calls)

    def test_package_validator_debian(self):
        cls = images.SaharaPackageValidator
        image_arguments = {"distro": 'ubuntu'}

        packages = [cls.Package("java", "8")]
        validator = images.SaharaPackageValidator(packages)
        remote = mock.Mock()
        validator.validate(remote, test_only=True,
                           image_arguments=image_arguments)
        remote.execute_command.assert_called_with(
            "dpkg -s java-8", run_as_root=True)

        image_arguments = {"distro": 'ubuntu'}
        packages = [cls.Package("java", "8"), cls.Package("hadoop")]
        validator = images.SaharaPackageValidator(packages)
        remote = mock.Mock()
        remote.execute_command.side_effect = (
            ex.RemoteCommandException("So bad!"))
        try:
            validator.validate(remote, test_only=True,
                               image_arguments=image_arguments)
        except p_ex.ImageValidationError as e:
            self.assertIn("So bad!", e.message)
        remote.execute_command.assert_called_with(
            "dpkg -s java-8 hadoop", run_as_root=True)
        self.assertEqual(remote.execute_command.call_count, 1)

        image_arguments = {"distro": 'ubuntu'}
        packages = [cls.Package("java", "8"), cls.Package("hadoop")]
        validator = images.SaharaPackageValidator(packages)
        remote = mock.Mock()
        remote.execute_command.side_effect = (
            ex.RemoteCommandException("So bad!"))
        try:
            validator.validate(remote, test_only=False,
                               image_arguments=image_arguments)
        except p_ex.ImageValidationError as e:
            self.assertIn("So bad!", e.message)
        self.assertEqual(remote.execute_command.call_count, 2)
        calls = [mock.call("dpkg -s java-8 hadoop", run_as_root=True),
                 mock.call("DEBIAN_FRONTEND=noninteractive " +
                           "apt-get -y install java-8 hadoop",
                           run_as_root=True)]
        remote.execute_command.assert_has_calls(calls)

    @mock.patch('oslo_utils.uuidutils.generate_uuid')
    def test_script_validator(self, uuid):
        hash_value = '00000000-0000-0000-0000-000000000000'
        uuidutils.generate_uuid.return_value = hash_value
        cls = images.SaharaScriptValidator
        image_arguments = {"distro": 'centos'}
        cmd = b"It's dangerous to go alone. Run this."
        validator = cls(cmd, env_vars=image_arguments.keys(),
                        output_var="distro")

        remote = mock.Mock(
            execute_command=mock.Mock(
                return_value=(0, 'fedora')))

        validator.validate(remote, test_only=False,
                           image_arguments=image_arguments)
        call = [mock.call('chmod +x /tmp/%(hash_value)s.sh' %
                          {'hash_value': hash_value}, run_as_root=True),
                mock.call('/tmp/%(hash_value)s.sh' %
                          {'hash_value': hash_value}, run_as_root=True)]
        remote.execute_command.assert_has_calls(call)
        self.assertEqual(image_arguments['distro'], 'fedora')

    def test_any_validator(self):
        cls = images.SaharaAnyValidator

        class FakeValidator(images.SaharaImageValidatorBase):

            def __init__(self, mock_validate):
                self.mock_validate = mock_validate

            def validate(self, remote, test_only=False, **kwargs):
                self.mock_validate(remote, test_only=test_only, **kwargs)

        # One success short circuits validation
        always_tells_the_truth = FakeValidator(mock.Mock())
        validator = cls([always_tells_the_truth, always_tells_the_truth])
        validator.validate(None, test_only=False)
        self.assertEqual(always_tells_the_truth.mock_validate.call_count, 1)

        # All failures fails, and calls with test_only=True on all first
        always_lies = FakeValidator(
            mock.Mock(side_effect=p_ex.ImageValidationError("Oh no!")))
        validator = cls([always_lies, always_lies])
        try:
            validator.validate(None, test_only=False)
        except p_ex.ImageValidationError:
            pass
        self.assertEqual(always_lies.mock_validate.call_count, 4)

        # But it fails after a first pass if test_only=True.
        always_lies = FakeValidator(
            mock.Mock(side_effect=p_ex.ImageValidationError("Oh no!")))
        validator = cls([always_lies, always_lies])
        try:
            validator.validate(None, test_only=True)
        except p_ex.ImageValidationError:
            pass
        self.assertEqual(always_lies.mock_validate.call_count, 2)

        # One failure doesn't end iteration.
        always_tells_the_truth = FakeValidator(mock.Mock())
        always_lies = FakeValidator(
            mock.Mock(side_effect=p_ex.ImageValidationError("Oh no!")))
        validator = cls([always_lies, always_tells_the_truth])
        validator.validate(None, test_only=False)
        self.assertEqual(always_lies.mock_validate.call_count, 1)
        self.assertEqual(always_tells_the_truth.mock_validate.call_count, 1)

    def test_all_validator(self):
        cls = images.SaharaAllValidator

        # All pass
        always_tells_the_truth = mock.Mock()
        validator = cls([always_tells_the_truth, always_tells_the_truth])
        validator.validate(None, test_only=False)
        self.assertEqual(always_tells_the_truth.validate.call_count, 2)
        always_tells_the_truth.validate.assert_called_with(
            None, test_only=False, image_arguments=None)

        # Second fails
        always_tells_the_truth = mock.Mock()
        always_lies = mock.Mock(validate=mock.Mock(
            side_effect=p_ex.ImageValidationError("Boom!")))
        validator = cls([always_tells_the_truth, always_lies])
        try:
            validator.validate(None, test_only=True)
        except p_ex.ImageValidationError:
            pass
        self.assertEqual(always_tells_the_truth.validate.call_count, 1)
        self.assertEqual(always_lies.validate.call_count, 1)
        always_tells_the_truth.validate.assert_called_with(
            None, test_only=True, image_arguments=None)
        always_lies.validate.assert_called_with(
            None, test_only=True, image_arguments=None)

        # First fails
        always_tells_the_truth = mock.Mock()
        always_lies = mock.Mock(validate=mock.Mock(
            side_effect=p_ex.ImageValidationError("Boom!")))
        validator = cls([always_lies, always_tells_the_truth])
        try:
            validator.validate(None, test_only=True, image_arguments={})
        except p_ex.ImageValidationError:
            pass
        self.assertEqual(always_lies.validate.call_count, 1)
        always_lies.validate.assert_called_with(
            None, test_only=True, image_arguments={})
        self.assertEqual(always_tells_the_truth.validate.call_count, 0)

    def test_os_case_validator(self):
        cls = images.SaharaOSCaseValidator
        Distro = images.SaharaOSCaseValidator._distro_tuple

        # First match wins and short circuits iteration
        centos = Distro("centos", mock.Mock())
        redhat = Distro("redhat", mock.Mock())
        distros = [centos, redhat]
        image_arguments = {images.SaharaImageValidator.DISTRO_KEY: "centos"}
        validator = cls(distros)
        validator.validate(None, test_only=False,
                           image_arguments=image_arguments)
        self.assertEqual(centos.validator.validate.call_count, 1)
        self.assertEqual(redhat.validator.validate.call_count, 0)
        centos.validator.validate.assert_called_with(
            None, test_only=False, image_arguments=image_arguments)

        # Families match
        centos = Distro("centos", mock.Mock())
        redhat = Distro("redhat", mock.Mock())
        distros = [centos, redhat]
        image_arguments = {images.SaharaImageValidator.DISTRO_KEY: "fedora"}
        validator = cls(distros)
        validator.validate(None, test_only=False,
                           image_arguments=image_arguments)
        self.assertEqual(centos.validator.validate.call_count, 0)
        self.assertEqual(redhat.validator.validate.call_count, 1)
        redhat.validator.validate.assert_called_with(
            None, test_only=False, image_arguments=image_arguments)

        # Non-matches do nothing
        centos = Distro("centos", mock.Mock())
        redhat = Distro("redhat", mock.Mock())
        distros = [centos, redhat]
        image_arguments = {images.SaharaImageValidator.DISTRO_KEY: "ubuntu"}
        validator = cls(distros)
        validator.validate(None, test_only=False,
                           image_arguments=image_arguments)
        self.assertEqual(centos.validator.validate.call_count, 0)
        self.assertEqual(redhat.validator.validate.call_count, 0)

    def test_sahara_argument_case_validator(self):
        cls = images.SaharaArgumentCaseValidator

        # Match gets called
        image_arguments = {"argument": "value"}
        match = mock.Mock()
        nomatch = mock.Mock()
        cases = {"value": match,
                 "another_value": nomatch}
        validator = cls("argument", cases)
        validator.validate(None, test_only=False,
                           image_arguments=image_arguments)
        self.assertEqual(match.validate.call_count, 1)
        self.assertEqual(nomatch.validate.call_count, 0)
        match.validate.assert_called_with(
            None, test_only=False, image_arguments=image_arguments)

        # Non-matches do nothing
        image_arguments = {"argument": "value"}
        nomatch = mock.Mock()
        cases = {"some_value": nomatch,
                 "another_value": nomatch}
        validator = cls("argument", cases)
        validator.validate(None, test_only=False,
                           image_arguments=image_arguments)
        self.assertEqual(nomatch.validate.call_count, 0)

    def test_sahara_argument_set_validator(self):
        cls = images.SaharaArgumentSetterValidator

        # Old variable is overwritten
        image_arguments = {"argument": "value"}
        validator = cls("argument", "new_value")
        validator.validate(None, test_only=False,
                           image_arguments=image_arguments)
        self.assertEqual(image_arguments["argument"], "new_value")

        # New variable is set
        image_arguments = {"argument": "value"}
        validator = cls("another_argument", "value")
        validator.validate(None, test_only=False,
                           image_arguments=image_arguments)
        self.assertEqual(image_arguments,
                         {"argument": "value", "another_argument": "value"})

    def test_sahara_image_validator(self):
        cls = images.SaharaImageValidator

        sub_validator = mock.Mock(validate=mock.Mock())
        remote = mock.Mock(get_os_distrib=mock.Mock(
            return_value="centos"))
        validator = cls(sub_validator, {})
        validator.validate(remote, test_only=False, image_arguments={})
        expected_map = {images.SaharaImageValidatorBase.DISTRO_KEY: "centos"}
        sub_validator.validate.assert_called_with(
            remote, test_only=False, image_arguments=expected_map)
        expected_map = {images.SaharaImageValidatorBase.DISTRO_KEY: "centos"}
        validator.validate(remote, test_only=True, image_arguments={})
        sub_validator.validate.assert_called_with(
            remote, test_only=True, image_arguments=expected_map)
