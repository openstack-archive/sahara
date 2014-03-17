Building Images for Vanilla Plugin
==================================

As of now vanilla plugin works with images with pre-installed Apache Hadoop. To
simplify task of building such images we use
`Disk Image Builder <https://github.com/openstack/diskimage-builder>`_.

`Disk Image Builder` is built of elements. An element is a particular set of
code that alters how the image is built, or runs within the chroot to prepare
the image.

Elements for building vanilla images are stored in `Sahara extra repository <https://github.com/openstack/sahara-image-elements>`_


.. note::

   Sahara requires images with cloud-init package installed:

   * `For Fedora <http://pkgs.fedoraproject.org/cgit/cloud-init.git/>`_
   * `For Ubuntu <http://packages.ubuntu.com/precise/cloud-init>`_

In this document you will find instruction on how to build Ubuntu and Fedora
images with Apache Hadoop.

1. Clone repository "https://github.com/openstack/sahara-image-elements" locally.

2. You just can run script diskimage-create.sh in any directory (for example, in home directory). This script will create two cloud images - Fedora and Ubuntu.

   .. sourcecode:: console

      sudo bash diskimage-create.sh

   This scripts will update your system and install required packages.
        * kpartx
        * qemu
   Then it will clone the repositories "https://github.com/openstack/diskimage-builder" and "https://github.com/openstack/sahara-image-elements" and export nessesary parameters.
        * ``DIB_HADOOP_VERSION`` - version of Hadoop to install
        * ``JAVA_DOWNLOAD_URL`` - download link for JDK (tarball or bin)
        * ``OOZIE_DOWNLOAD_URL`` - download link for OOZIE (we have built
   Oozie libs here: http://sahara-files.mirantis.com/oozie-4.0.0.tar.gz
        * ``HIVE_VERSION`` - version of Hive to install (currently supports only 0.11.0)
        * ``ubuntu_image_name``
        * ``fedora_image_name``
        * ``DIB_IMAGE_SIZE`` - parameter that specifies a volume of hard disk of
          instance. You need to specify it only for Fedora because Fedora doesn't use all available volume
        * ``DIB_COMMIT_ID`` - latest commit id of diksimage-builder project
        * ``SAHARA_ELEMENTS_COMMIT_ID`` - latest commit id of sahara-image-elements project

   NOTE: If you don't want to use default values, you should edit this script and set your values of parameters.

   Then it will create two cloud image with ``hadoop``, ``hive``, ``oozie``, ``mysql``, ``swift_hadoop`` elements that install all necessary packages and configure them. You will find these images in current directory.
