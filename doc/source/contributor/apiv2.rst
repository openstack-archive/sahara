API Version 2 Development
=========================

The sahara project is currently in the process of creating a new
RESTful application programming interface (API). This interface is
by-default enabled, although it remains experimental.

This document defines the steps necessary to enable and communicate
with the new API. This API has a few fundamental changes from the
previous APIs and they should be noted before proceeding with
development work.

.. warning::
    This API is currently marked as experimental. It is not supported
    by the sahara python client. These instructions are included purely
    for developers who wish to help participate in the development
    effort.

Enabling the experimental API
-----------------------------

There are a few changes to the WSGI pipeline that must be made to
enable the new v2 API. These changes will leave the 1.0 and 1.1 API
versions in place and will not adjust their communication parameters.

To begin, uncomment, or add, the following sections in your
api-paste.ini file:

.. sourcecode:: ini

    [app:sahara_apiv2]
    paste.app_factory = sahara.api.middleware.sahara_middleware:RouterV2.factory

    [filter:auth_validator_v2]
    paste.filter_factory = sahara.api.middleware.auth_valid:AuthValidatorV2.factory

These lines define a new authentication filter for the v2 API, and
define the application that will handle the new calls.

With these new entries in the paste configuration, we can now enable
them with the following changes to the api-paste.ini file:

.. sourcecode:: ini

    [pipeline:sahara]
    pipeline = cors request_id acl auth_validator_v2 sahara_api

    [composite:sahara_api]
    use = egg:Paste#urlmap
    /: sahara_apiv2

There are 2 significant changes occurring here; changing the
authentication validator in the pipeline, and changing the root "/"
application to the new v2 handler.

At this point the sahara API server should be configured to accept
requests on the new v2 endpoints.

Communicating with the v2 API
-----------------------------

The v2 API makes at least one major change from the previous versions,
removing the OpenStack project identifier from the URL. Now users of
the API do not provide their project ID explictly; instead we fully
trust keystonemiddeware to provide it in the WSGI environment based
on the given user token.

For example, in previous versions of the API, a call to get the list of
clusters for project "12345678-1234-1234-1234-123456789ABC" would have
been made as follows::

    GET /v1.1/12345678-1234-1234-1234-123456789ABC/clusters
    X-Auth-Token: {valid auth token}

This call would now be made to the following URL::

    GET /v2/clusters
    X-Auth-Token: {valid auth token}

Using a tool like `HTTPie <https://httpie.org/>`_, the
same request could be made like this::

    $ httpie http://{sahara service ip:port}/v2/clusters \
      X-Auth-Token:{valid auth token}

Following the implementation progress
-------------------------------------

As the creation of this API will be under regular change until it moves
out of the experimental phase, a wiki page has been established to help
track the progress.

https://wiki.openstack.org/wiki/Sahara/api-v2

This page will help to coordinate the various reviews, specs, and work
items that are a continuing facet of this work.

The API service layer
---------------------

When contributing to the version 2 API, it will be necessary to add code
that modifies the data and behavior of HTTP calls as they are sent to
and from the processing engine and data abstraction layers. Most
frequently in the sahara codebase, these interactions are handled in the
modules of the ``sahara.service.api`` package. This package contains
code for all versions of the API and follows a namespace mapping that is
similar to the routing functions of ``sahara.api``

Although these modules are not the definitive end of all answers to API
related code questions, they are a solid starting point when examining
the extent of new work. Furthermore, they serve as a central point to
begin API debugging efforts when the need arises.
