Savanna project
===============

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

4. Run PEP8 (style) and PyFlakes (static analysis) checks:
::
    tools/run_fast_checks

5. Build docs:
::
    tools/build_docs

6. Run all tests:
::
    tools/run_tests

7. Run Savanna REST API with stub data and cluster ops on port 8080
::
    .venv/bin/python bin/savanna-api --reset-db --stub-data --allow-cluster-ops


Pip speedup
-----------

Add the following lines to ~/.pip/pip.conf
::
    [global]
    download-cache = /home/<username>/.pip/cache
    index-url = <mirror url>

Note! The ~/.pip/cache folder should be created.

Git hook for fast checks
------------------------
Just add the following lines to .git/hooks/pre-commit and do chmod +x for it.
::
    #!/bin/sh
    # Run fast checks (PEP8 style check and PyFlakes fast static analysis)
    tools/run_fast_checks

You can added the same check for pre-push, for example, run_tests and run_pylint.

Running static analysis (PyLint)
--------------------------------
Just run the following command
::
    tools/run_pylint

License
-------
Copyright (c) 2013 Mirantis Inc.

Apache License Version 2.0 http://www.apache.org/licenses/LICENSE-2.0
