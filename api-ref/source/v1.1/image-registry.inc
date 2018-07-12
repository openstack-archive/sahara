.. -*- rst -*-

==============
Image registry
==============

Use the image registry tool to manage images, add tags to and
remove tags from images, and define the user name for an instance
operating system. Each plugin lists required tags for an image. To
run remote operations, the Data Processing service requires a user
name with which to log in to the operating system for an instance.


Add tags to image
=================

.. rest_method::  POST /v1.1/{project_id}/images/{image_id}/tag

Adds tags to an image.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - tags: tags
   - image_id: url_image_id

Request Example
---------------

.. literalinclude:: samples/image-registry/image-tags-add-request.json
   :language: javascript







Show image details
==================

.. rest_method::  GET /v1.1/{project_id}/images/{image_id}

Shows details for an image.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - image_id: url_image_id


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - status: status
   - username: username
   - updated: updated
   - description: image_description
   - created: created
   - image: image
   - tags: tags
   - minDisk: minDisk
   - name: image_name
   - progress: progress
   - minRam: minRam
   - id: image_id
   - metadata: metadata



Response Example
----------------

.. literalinclude:: samples/image-registry/image-show-response.json
   :language: javascript




Register image
==============

.. rest_method::  POST /v1.1/{project_id}/images/{image_id}

Registers an image in the registry.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - username: username
   - description: image_description
   - image_id: url_image_id

Request Example
---------------

.. literalinclude:: samples/image-registry/image-register-request.json
   :language: javascript



Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - status: status
   - username: username
   - updated: updated
   - description: image_description
   - created: created
   - image: image
   - tags: tags
   - minDisk: minDisk
   - name: image_name
   - progress: progress
   - minRam: minRam
   - id: image_id
   - metadata: metadata





Unregister image
================

.. rest_method::  DELETE /v1.1/{project_id}/images/{image_id}

Removes an image from the registry.

Normal response codes:204


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - image_id: url_image_id






Remove tags from image
======================

.. rest_method::  POST /v1.1/{project_id}/images/{image_id}/untag

Removes tags from an image.

Normal response codes:202


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - tags: tags
   - image_id: url_image_id

Request Example
---------------

.. literalinclude:: samples/image-registry/image-tags-delete-request.json
   :language: javascript







List images
===========

.. rest_method::  GET /v1.1/{project_id}/images

Lists all images registered in the registry.


Normal response codes: 200


Request
-------

.. rest_parameters:: parameters.yaml

   - project_id: url_project_id
   - tags: tags


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - status: status
   - username: username
   - updated: updated
   - description: image_description
   - created: created
   - image: image
   - tags: tags
   - minDisk: minDisk
   - name: image_name
   - images: images
   - progress: progress
   - minRam: minRam
   - id: image_id
   - metadata: metadata



Response Example
----------------

.. literalinclude:: samples/image-registry/images-list-response.json
   :language: javascript



