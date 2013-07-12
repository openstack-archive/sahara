Development Guidelines
======================

Coding Guidelines
-----------------

For all the code in Savanna we have a rule - it should pass `PEP 8`_.

To check your code against PEP 8 run:

.. sourcecode:: console

    $ tox -e pep8

.. note::
  For more details on coding guidelines see file ``HACKING.rst`` in the root
  of Savanna repo.


Testing Guidelines
------------------

Savanna has a suite of tests that are run on all submitted code,
and it is recommended that developers execute the tests themselves to
catch regressions early.  Developers are also expected to keep the
test suite up-to-date with any submitted code changes.

Unit tests are located at ``savanna/tests``.

Savanna's suite of unit tests can be executed in an isolated environment
with `Tox`_. To execute the unit tests run the following from the root of
Savanna repo:

.. sourcecode:: console

    $ tox -e py27


Documentation Guidelines
------------------------

All Savanna docs are written using Sphinx / RST and located in the main repo
in ``doc`` directory. You can add/edit pages here to update
https://savanna.readthedocs.org/en/latest/ site.

The documentation in docstrings should follow the `PEP 257`_ conventions
(as mentioned in the `PEP 8`_ guidelines).

More specifically:

1. Triple quotes should be used for all docstrings.
2. If the docstring is simple and fits on one line, then just use
   one line.
3. For docstrings that take multiple lines, there should be a newline
   after the opening quotes, and before the closing quotes.
4. `Sphinx`_ is used to build documentation, so use the restructured text
   markup to designate parameters, return values, etc.  Documentation on
   the sphinx specific markup can be found here:



Run the following command to build docs locally.

.. sourcecode:: console

    $ tox -e docs

After it you can access generated docs in ``doc/build/`` directory, for example,
main page - ``doc/build/html/index.html``.

To make docs generation process faster you can use:

.. sourcecode:: console

    $ SPHINX_DEBUG=1 tox -e docs

or to avoid savanna reinstallation to virtual env each time you want to rebuild
docs you can use the following command (it could be executed only after
running ``tox -e docs`` first time):

.. sourcecode:: console

    $ SPHINX_DEBUG=1 .tox/docs/bin/python setup.py build_sphinx



.. note::
  For more details on documentation guidelines see file HACKING.rst in the root
  of Savanna repo.


.. _PEP 8: http://www.python.org/dev/peps/pep-0008/
.. _PEP 257: http://www.python.org/dev/peps/pep-0257/
.. _Tox: http://tox.testrun.org/
.. _Sphinx: http://sphinx.pocoo.org/markup/index.html
