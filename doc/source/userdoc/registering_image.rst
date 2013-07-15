Registering Image
=================

Savanna deploys cluster of machines based on images stored in Glance.
Each plugin has its own requirements on image contents, see specific plugin
documentation for details. A general requirement for an image is to have
cloud-init package installed.

Savanna requires image to be registered in Savanna Image Registry order to work with it.
A registered image must have two properties:
 * username - a name of the default cloud-init user
 * tags - certain tags mark image to be suitable for certain plugins. See plugins documentation for details.
