==============================
EDP with S3-like Object Stores
==============================

Overview and rationale of S3 integration
========================================
Since the Rocky release, Sahara clusters have full support for interaction with
S3-like object stores, for example Ceph Rados Gateway. Through the abstractions
offered by EDP, a Sahara job execution may consume input data and job binaries
stored in S3, as well as write back its output data to S3.

The copying of job binaries from S3 to a cluster is performed by the botocore
library. A job's input and output to and from S3 is handled by the Hadoop-S3A
driver.

It's also worth noting that the Hadoop-S3A driver may be more mature and
performant than the Hadoop-SwiftFS driver (either as hosted by Apache or in
the sahara-extra respository).

Sahara clusters are also provisioned such that data in S3-like storage can also
be accessed when manually interacting with the cluster; in other words: the
needed libraries are properly situated.

Considerations for deployers
============================
The S3 integration features can function without any specific deployment
requirement. This is because the EDP S3 abstractions can point to an arbitrary
S3 endpoint.

Deployers may want to consider using Sahara's optional integration with secret
storage to protect the S3 access and secret keys that users will provide. Also,
if using Rados Gateway for S3, deployers may want to use Keystone for RGW auth
so that users can simply request Keystone EC2 credentials to access RGW's S3.

S3 user experience
==================
Below, details about how to use the S3 integration features are discussed.

EDP job binaries in S3
----------------------
The ``url`` must be in the format ``s3://bucket/path/to/object``, similar to
the format used for binaries in Swift. The ``extra`` structure must contain
``accesskey``, ``secretkey``, and ``endpoint``, which is the URL of the S3
service, including the protocol ``http`` or ``https``.

As mentioned above, the binary will be copied to the cluster before execution,
by use of the botocore library. This also means that the set of credentials
used to access this binary may be entirely different than those for accessing
a data source.

EDP data sources in S3
----------------------
The ``url`` should be in the format ``s3://bucket/path/to/object``, although
upon execution the protocol will be automatically changed to ``s3a``. The
``credentials`` does not have any required values, although the following may
be set:

* ``accesskey`` and ``secretkey``
* ``endpoint``, which is the URL of the S3 service, without the protocl
* ``ssl``, which must be a boolean
* ``bucket_in_path``, to indicate whether the S3 service uses
  virtual-hosted-style or path-style URLs, and must be a boolean

The values above are optional, as they may be set in the cluster's
``core-site.xml`` or as configuration values of the job execution, as follows,
as dictated by the options understood by the Hadoop-S3A driver:

* ``fs.s3a.access.key``, corresponding to ``accesskey``
* ``fs.s3a.secret.key``, corresponding to ``secretkey``
* ``fs.s3a.endpoint``, corresponding to ``endpoint``
* ``fs.s3a.connection.ssl.enabled``, corresponding to ``ssl``
* ``fs.s3a.path.style.access``, corresponding to ``bucket_in_path``

In the case of ``fs.s3a.path.style.access``, a default value is determined by
the Hadoop-S3A driver if none is set: virtual-hosted-style URLs are assumed
unless told otherwise, or if the endpoint is a raw IP address.

Additional configuration values are supported by the Hadoop-S3A driver, and are
discussed in its official documentation.

It is recommended that the EDP data source abstraction is used, rather than
handling bare arguments and configuration values.

If any S3 configuration values are to be set at execution time, including such
situations in which those values are contained by the EDP data source
abstraction, then ``edp.spark.adapt_for_swift`` or ``edp.java.adapt_for_oozie``
must be set to ``true`` as appropriate.
