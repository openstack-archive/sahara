Elastic Hadoop on OpenStack
===========================

QuickStart (Ubuntu)
----------
1. Install Python with headers and virtualenv:
::
    apt-get install python-dev python-virtualenv

2. Prepare virtual environment:
::
    tools/install_venv

3. To run Python fro created environment just call:
::
    tools/with_venv python

4. Run PEP8 checks:
::
    tools/run_pep8

5. Build docs:
::
    tools/build_docs

6. Run all tests:
::
    tools/run_tests


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

You can added the same check for pre-push, for example, run all tests.
