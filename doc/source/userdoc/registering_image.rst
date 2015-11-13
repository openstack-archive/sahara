Registering an Image
====================

Sahara deploys a cluster of machines using images stored in Glance.

Each plugin has its own requirements on the image contents (see specific plugin
documentation for details). Two general requirements for an image are to have
the cloud-init and the ssh-server packages installed.

Sahara requires the images to be registered in the Sahara Image Registry.
A registered image must have two properties set:

* username - a name of the default cloud-init user.
* tags - certain tags mark image to be suitable for certain plugins.

The username depends on the image that is used and the tags depend on the
plugin used.  You can find both in the respective plugin's documentation.
