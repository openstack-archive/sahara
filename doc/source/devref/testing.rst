Sahara Testing
==============

We have a bunch of different tests for Sahara.

Unit Tests
++++++++++

In most Sahara sub repositories we have `_package_/tests/unit` or
`_package_/tests` that contains Python unit tests.

Scenario integration tests
++++++++++++++++++++++++++

New scenario integration tests were implemented in Sahara, you can see how
use and run it here: `sahara/tests/scenario/README.rst`

Tempest tests
+++++++++++++

We have some tests in Tempest (https://github.com/openstack/tempest) that are
testing Sahara. Here is a list of currently implemented tests:

* REST API tests are checking how the Sahara REST API works.
  The only part that is not tested is cluster creation, more info about api
  tests - http://docs.openstack.org/developer/tempest/field_guide/api.html

* CLI tests are checking read-only operations using the Sahara CLI, more info -
  http://docs.openstack.org/developer/tempest/field_guide/cli.html
