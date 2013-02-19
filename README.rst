Elastic Hadoop on Openstack
===========================

Quickstart
----------
::

    # tools/install_venv
    # tools/with_venv python
    # tools/build_docs
    # tools/run_pep8
    # tools/run_tests


Pip speedup
-----------

Add the following lines to ~/.pip/pip.conf
::
    # [global]
    # download-cache = /home/<username>/.pip/cache
    # index-url = <mirror url> 

Note! The ~/.pip/cache folder should be created.
For Saratov location the http://mirrors.sgu.ru/pypi/simple is preferred.

Git hook for pep8 check
-----------------------
Just add the following lines to .git/hooks/pre-commit and do chmod +x for it.
::
    #!/bin/sh
    # Auto-check for pep8
    tools/run_pep8
