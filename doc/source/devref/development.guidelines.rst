Development Guidelines
======================

Coding Guidelines
-----------------

For all the code in Savanna we have a rule - it should pass `PEP 8`_.

To check your code against PEP 8 run:

.. sourcecode:: bash

  tox -e pep8

.. note::
  For more details on coding guidelines see file ``HACKING.rst`` in the root of Savanna repo.


Testing Guidelines
------------------

Savanna has a suite of tests that are run on all submitted code,
and it is recommended that developers execute the tests themselves to
catch regressions early.  Developers are also expected to keep the
test suite up-to-date with any submitted code changes.

Savanna's suite of unit tests can be executed in an isolated environment
with `Tox`_. To execute the unit tests run the following from the root of Savanna repo:

.. sourcecode:: bash

    tox -e py27


Documentation Guidelines
------------------------

The documentation in docstrings should follow the `PEP 257`_ conventions
(as mentioned in the `PEP 8`_ guidelines).

More specifically:

    1.  Triple quotes should be used for all docstrings.
    2.  If the docstring is simple and fits on one line, then just use
        one line.
    3.  For docstrings that take multiple lines, there should be a newline
        after the opening quotes, and before the closing quotes.
    4.  `Sphinx`_ is used to build documentation, so use the restructured text
        markup to designate parameters, return values, etc.  Documentation on
        the sphinx specific markup can be found here:



To build documentation execute. You will find html pages at ``doc/build/html``:

.. sourcecode:: bash

    tox -e docs


.. note::
  For more details on documentation guidelines see file HACKING.rst in the root of Savanna repo.


.. _PEP 8: http://www.python.org/dev/peps/pep-0008/
.. _PEP 257: http://www.python.org/dev/peps/pep-0257/
.. _Tox: http://tox.testrun.org/
.. _Sphinx: http://sphinx.pocoo.org/markup/index.html