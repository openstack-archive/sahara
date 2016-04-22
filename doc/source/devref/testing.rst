Sahara Testing
==============

We have a bunch of different tests for Sahara.

Unit Tests
++++++++++

In most Sahara sub repositories we have `_package_/tests/unit` or
`_package_/tests` that contains Python unit tests.

Scenario integration tests
++++++++++++++++++++++++++

New scenario integration tests were implemented for Sahara, they are available
in the sahara-tests repository (https://git.openstack.org/cgit/openstack/sahara-tests).

Tempest tests
+++++++++++++

We have some tests based on Tempest (https://git.openstack.org/cgit/openstack/tempest)
that tests Sahara. Here is a list of currently implemented tests:

* REST API tests are checking how the Sahara REST API works.
  The only part that is not tested is cluster creation, more info about api
  tests - http://docs.openstack.org/developer/tempest/field_guide/api.html

* CLI tests are checking read-only operations using the Sahara CLI, more info -
  http://docs.openstack.org/developer/tempest/field_guide/cli.html
