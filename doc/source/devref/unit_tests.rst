Unit Tests
====================================

Savanna contains a suite of unit tests, in the savanna/tests directory.

Any proposed code change will be automatically rejected by the OpenStack
Jenkins server [#f1]_ if the change causes unit test failures.


Running the tests
-----------------
Run the unit tests by doing:

.. sourcecode:: bash

    ./tools/run_tests.sh



.. rubric:: Footnotes

.. [#f1] See :doc:`jenkins`.