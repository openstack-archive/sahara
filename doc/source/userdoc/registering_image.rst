Registering an Image
====================

Sahara deploys cluster of machines based on images stored in Glance.
Each plugin has its own requirements on image contents, see specific plugin
documentation for details. A general requirement for an image is to have
cloud-init package installed.

Sahara requires image to be registered in Sahara Image Registry order to work with it.
A registered image must have two properties set:

* username - a name of the default cloud-init user.
* tags - certain tags mark image to be suitable for certain plugins.

Username depends on image used. Tags depend on the plugin used.
You can find both in the respective plugin's documentation.
