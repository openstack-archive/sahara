Savanna project
===============

Project blueprint: https://wiki.openstack.org/wiki/Savanna | http://savanna.mirantis.com/index.html
Architecture draft: https://wiki.openstack.org/wiki/Savanna/Architecture | http://savanna.mirantis.com/architecture.html
Roadmap: https://wiki.openstack.org/wiki/Savanna/Roadmap | http://savanna.mirantis.com/roadmap.html
API draft: http://savanna.mirantis.com/restapi/v02.html
Launchpad project: https://launchpad.net/savanna

QuickStart (Ubuntu)
----------

Please, take a look at http://savanna.mirantis.com/quickstart.html


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
