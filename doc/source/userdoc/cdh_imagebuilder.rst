.. _cdh_diskimage-builder-label:

Building Images for Cloudera Plugin
===================================

In this document you will find instructions on how to build Ubuntu and CentOS
images with Cloudera Express (now only 5.0.0 and 5.3.0 versions are supported).

Apache Hadoop. To simplify the task of building such images we use
`Disk Image Builder <https://github.com/openstack/diskimage-builder>`_.

`Disk Image Builder` builds disk images using elements. An element is a
particular set of code that alters how the image is built, or runs within the
chroot to prepare the image.

Elements for building Cloudera images are stored in
`Sahara extra repository <https://github.com/openstack/sahara-image-elements>`_

.. note::

   Sahara requires images with cloud-init package installed:

   * `For CentOS <http://mirror.centos.org/centos/6/extras/x86_64/Packages/cloud-init-0.7.5-10.el6.centos.2.x86_64.rpm>`_
   * `For Ubuntu <http://packages.ubuntu.com/precise/cloud-init>`_

To create cloudera images follow these steps:

1. Clone repository "https://github.com/openstack/sahara-image-elements" locally.

2. Run the diskimage-create.sh script.

   You can run the script diskimage-create.sh in any directory (for example, in
   your home directory). By default this script will attempt to create cloud
   images for all versions of supported plugins and all operating systems
   (subset of Ubuntu, Fedora, and CentOS depending on plugin). To only create
   Cloudera images, you should use the "-p cloudera" parameter in the command
   line. If you want to create the image only for a specific operating system,
   you should use the "-i ubuntu|centos" parameter to assign the operating
   system (the cloudera plugin only supports Ubuntu and Centos). If you want
   to create the image only for a specific Cloudera version, you should use the
   "-v 5.0|5.3" parameter to assign the version. This script must be run with
   root privileges. Below is an example to create Cloudera images for both
   Ubuntu and CentOS with Cloudera Express 5.3.0 version.

   .. sourcecode:: console

      sudo bash diskimage-create.sh -p cloudera -v 5.3

   NOTE: If you don't want to use default values, you should explicitly set the
   values of your required parameters.

   The script will create required cloud images using image elements that install
   all the necessary packages and configure them. You will find the created
   images in the current directory.

.. note::

    Disk Image Builder will generate QCOW2 images, used with the default
    OpenStack Qemu/KVM hypervisors. If your OpenStack uses a different
    hypervisor, the generated image should be converted to an appropriate
    format.

    The VMware Nova backend requires the VMDK image format. You may use qemu-img
    utility to convert a QCOW2 image to VMDK.

    .. sourcecode:: console

        qemu-img convert -O vmdk <original_image>.qcow2 <converted_image>.vmdk


For finer control of diskimage-create.sh see the `official documentation
<https://github.com/openstack/sahara-image-elements/blob/master/diskimage-create/README.rst>`_
or run:

.. sourcecode:: console

   $ diskimage-create.sh -h
