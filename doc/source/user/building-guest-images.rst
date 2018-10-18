.. _building-guest-images-label:

Building guest images
=====================

Sahara plugins represent different Hadoop or other Big Data platforms
and requires specific guest images.

While it is possible to use cloud images which only contain the basic
software requirements (also called *plain images*), their usage slows down
the cluster provisioning process and was not throughly tested recently.

It is strongly advised to build images which contain
the software required to create the clusters for the various plugins
and use them instead of *plain images*.

Sahara currently provides two different tools for building
guest images:
- ``sahara-image-pack`` is newer and support more recent images;
- ``sahara-image-create`` is the older tool.

Both tools are described in the details in the next sections.

The documentation of each plugin describes which method is supported
for the various versions. If both are supported, ``sahara-image-pack``
is recommended.

General requirements for guest images
-------------------------------------

There are few common requirements for all guest images,
which must be based on GNU/Linux distributions.

* cloud-init must be installed
* the ssh server must be installed
* the firewall, if enabled, must allow connections on port 22 (ssh)

The cloud images provided by the GNU/Linux distributions respect
those requirements.

Each plugin specifies additional requirements.
The image building tools provided by Sahara take care of preparing the images
with those additional requirements.

.. toctree::

   building-guest-images/sahara-image-pack
   building-guest-images/sahara-image-create
   building-guest-images/baremetal
