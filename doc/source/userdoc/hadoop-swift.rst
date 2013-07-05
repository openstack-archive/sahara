Swift integration
=================
Hadoop and Swift integration is the essential continuation of Hadoop&OpenStack marriage. There were two steps to achieve this:

* Hadoop side: a FileSystem implementation for Swift: https://issues.apache.org/jira/browse/HADOOP-8545. This patch is not merged yet and is still being developed, so that's why there is an ability to get the latest-version jar file from extra-repository: https://github.com/stackforge/savanna-extra/blob/master/hadoop-swift/hadoop-swift-latest.jar . Of cource, you may build jar-file by yourself.

* Swift side: https://review.openstack.org/#/c/21015/. This patch is merged into Grizzly. But if you want to make it work in Folsom please see the instructions in the section below.


Swift patching
--------------
If you are still using Folsom you need to follow these steps:

* Go to proxy server and find proxy-server.conf file. Go to [pipeline-main] section and insert a new filter BEFORE 'authtoken' filter. The name of your new filter is not very important, you will use it only for configuration. E.g. let it be ${list_endpoints}:
.. sourcecode:: bash

    [pipeline:main]
    pipeline = catch_errors healthcheck cache ratelimit swift3 s3token list_endpoints authtoken keystone proxy-server

The next thing you need to do here is to add the description of new filter:

.. sourcecode:: bash

    [filter:list_endpoints]
    use = egg:swift#${list_endpoints}
    # list_endpoints_path = /endpoints/

list_endpoints_path is not mandatory and is "endpoints" by default. This param is used for http-request construction. See details below.

* Go to entry_points.txt in egg-info. For swift-1.7.4 it may be found in /usr/lib/python2.7/dist-packages/swift-1.7.4.egg-info/entry_points.txt. Add the following description
   to [paste.filter_factory] section:

.. sourcecode:: bash

    ${list_endpoints} = swift.common.middleware.list_endpoints:filter_factory

* And the last step: put https://review.openstack.org/#/c/21015/7/swift/common/middleware/list_endpoints.py to /python2.7/dist-packages/swift/common/middleware/.

Is Swift was patched successfully?
----------------------------------
You may check if patching is successful just sending the following http requests:

.. sourcecode:: bash

    http://${proxy}:8080/endpoints/${account}/${container}/${object}
    http://${proxy}:8080/endpoints/${account}/${container}
    http://${proxy}:8080/endpoints/${account}

You don't need any additional headers here and authorization (see previous section: filter ${list_endpoints} is before 'authtoken' filter). The response will contain ip's of all swift nodes which contains the corresponding object.


Hadoop patching
---------------
You may build jar file by yourself choosing the latest patch from https://issues.apache.org/jira/browse/HADOOP-8545. Or you may get the latest one from repository https://review.openstack.org/#/q/project:stackforge/savanna-extra,n,z
You need to put this file to hadoop libraries (e.g. /usr/lib/share/hadoop/lib) into each job-tracker and task-tracker node in cluster. The main step in this section is to configure core-site.xml
file on each of this node.

Hadoop configurations
---------------------
All of configs may be rewritten by Hadoop-job or set in core-site.xml using this template:

.. sourcecode:: xml

    <property>
        <name>${name} + ${config}</name>
        <value>${value}</value>
        <description>${not mandatory description}</description>
    </property>


There are two types of configs here:

1. General. The ${name} in this case equals to "fs.swift".
Here is the list of ${config}:
* ".impl".
   Swift FileSystem implementation. The ${value} is "org.apache.hadoop.fs.swift.snative.SwiftNativeFileSystem".
* ".connect.timeout"
   Timeout for all connections by default: 15000
* ".socket.timeout"
        how long the connection waits for responses from servers. by default: 60000
* ".connect.retry.count"
        connection retry count for all connections. by default: 3
* ".connect.throttle.delay"
        delay in millis between bulk (delete, rename, copy operations). by default: 0
* ".blocksize"
        blocksize for filesystem. By default: 32Mb
* ".partsize"
        The partition size for uploads. By default: 4608*1024Kb
* ".requestsize"
        request size for reads in KB. By default: 64Kb



2. Provider-specific. Patch for Hadoop supports different cloud providers(e.g. can read from RackSpace Object Store, write to HP Public Cloud Store).
The ${name} in this case equals to "fs.swift.service.${provider}".

Here is the list of ${config}:

* ".auth.url"
    Authorization URL
* ".tenant"
* ".username"
* ".password"
* ".http.port"
* ".https.port"
* ".region"
    Swift region is used when cloud has more than one Swift installation. If region param is not set first region from Keystone endpoint list will be chosen. If region param not found exception will be thrown.
* ".location-aware"
    Turn On location awareness. Is false by default
* ".apikey"
* ".public"
Some cloud providers offer two kind of urls: public and internal (for example RackSpace internal urls network bandwidth is better than public ones, so for services in RackSpace cloud better to use iternal ones). By default this feature is turned off

Example
-------
By this point Swift and Hadoop is ready for use. All configs in hadoop is ok.

In example below provider's name is "rackspace".
So let's copy one object to another in one swift container and account. E.g. /dev/integration/temp to /dev/integration/temp1. Will use distcp for this purpose: http://hadoop.apache.org/docs/r0.19.0/distcp.html .
How to write swift path? In our case it will look as follows: swift://integration.rackspace/temp. So the template is: swift://${container}.${provider}/${object}. We don't need to point out the account because
it will be automatically determined from tenant name from configs. Actually, account=tenant.

Let's run the job:

.. sourcecode:: bash

    hadoop distcp swift://integration.rackspace/temp swift://integration.rackspace/temp1

After that just check if temp1 is created.

Limitations
-----------

**Note:** Please note that container name should be a valid URI.





















