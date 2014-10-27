Registering an Image
====================

Sahara deploys a cluster of machines based on images stored in Glance.
Each plugin has its own requirements on image contents, see specific plugin
documentation for details. A general requirement for an image is to have the
cloud-init package installed.

Sahara requires the image to be registered in the Sahara Image Registry in order to work with it.
A registered image must have two properties set:

* username - a name of the default cloud-init user.
* tags - certain tags mark image to be suitable for certain plugins.

The username depends on the image that is used and tags depend on the plugin used.
You can find both in the respective plugin's documentation.
