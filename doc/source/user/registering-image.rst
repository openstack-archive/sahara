Registering an Image
====================

Sahara deploys a cluster of machines using images stored in Glance.

Each plugin has its own requirements on the image contents (see specific plugin
documentation for details). Two general requirements for an image are to have
the cloud-init and the ssh-server packages installed.

Sahara requires the images to be registered in the Sahara Image Registry.
A registered image must have two properties set:

* username - a name of the default cloud-init user.
* tags - certain tags mark image to be suitable for certain plugins. The tags
  depend on the plugin used, you can find required tags in the plugin's
  documentations.

The default username specified for these images is different
for each distribution:

+--------------+------------+
| OS           | username   |
+==============+============+
| Ubuntu 14.04 | ubuntu     |
+--------------+------------+
| Ubuntu 16.04 | ubuntu     |
+--------------+------------+
| Fedora       | fedora     |
+--------------+------------+
| CentOS 7.x   | centos     |
+--------------+------------+
