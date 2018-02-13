Build Sahara Images with CLI

**Role Variables**

.. zuul:rolevar:: sahara_build_directory
   :default: /var/tmp/sahara-image-build

   The base directory used for the build process.

.. zuul:rolevar:: sahara_plugin
   :default: vanilla

   The plugin whose images will be built.
