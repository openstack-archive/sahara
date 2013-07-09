How to contribute to Docs
=========================

All Savanna docs are written using Sphinx / RST and located in the main repo
in ``doc`` directory. You can add/edit pages here to update
https://savanna.readthedocs.org/en/latest/ site.


Building docs
-------------

You should run the following command to build docs locally.

.. sourcecode:: console

    $ tox -e docs

After it you can access builded docs in ``doc/build/`` directory, for example,
main page - ``doc/build/html/index.html``.

For developers needs you can make docs building faster using the following
command :

.. sourcecode:: console

    $ SPHINX_DEBUG=1 tox -e docs

or to avoid savanna reinstallation to virtual env each time you want to rebuild
docs you can use the following command (it could be executed only after
running ``tox -e docs`` first time):

.. sourcecode:: console

    $ SPHINX_DEBUG=1 .tox/docs/bin/python setup.py build_sphinx
