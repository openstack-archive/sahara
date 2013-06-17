import mock
import unittest2

from savanna import context
import savanna.swift.swift_helper as h
from savanna.utils import patches

GENERAL_PREFIX = "fs.swift."
SERVICE_PREFIX = "service.savanna."

GENERAL = ["impl", "connect.timeout", "socket.timeout",
           "connect.retry.count", "connect.throttle.delay",
           "blocksize", "partsize", "requestsize"]

SERVICE_SPECIFIC = ["auth.url", "tenant",
                    "username", "password", "http.port",
                    "https.port", "public", "location-aware",
                    "region", "apikey"]


class SwiftIntegrationTestCase(unittest2.TestCase):
    def setUp(self):
        patches.patch_minidom_writexml()
        context.set_ctx(
            context.Context('test_user', 'test_tenant', 'test_auth_token',
                            {'X-Tenant-Name': "test_tenant"}))

    def test_get_configs_names(self):
        result = h.get_configs_names()
        for g in GENERAL:
            self.assertIn(GENERAL_PREFIX + g, result)

        for s_s in SERVICE_SPECIFIC:
            self.assertIn(GENERAL_PREFIX + SERVICE_PREFIX + s_s, result)

    def test__initialise_configs(self):
        result = h._initialise_configs()
        all_keys = h.get_configs_names()
        for name in all_keys:
            self.assertIn(name, result)

        self.assertEqual(result["fs.swift.service.savanna.public"], "true")
        self.assertEqual(result["fs.swift.impl"],
                         "org.apache.hadoop.fs.swift."
                         "snative.SwiftNativeFileSystem")

    @mock.patch('savanna.swift.swift_helper._retrieve_auth_url')
    def test_get_swift_configs(self, authUrlConfig):
        authUrlConfig.return_value = "http://localhost:8080/v2.0/tokens"

        result = h.get_swift_configs()
        self.assertEqual(7, len(result))
        self.assertEqual(result["fs.swift.service.savanna.location-aware"],
                         "true")
        self.assertEqual(result["fs.swift.service.savanna.tenant"],
                         "test_tenant")
        self.assertEqual(result["fs.swift.service.savanna.http.port"], "8080")
