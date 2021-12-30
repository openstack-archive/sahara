sahara-image-create
-------------------

The historical tool for building images, ``sahara-image-create``, is based on
`Disk Image Builder <https://opendev.org/openstack/diskimage-builder>`_.

`Disk Image Builder` builds disk images using elements. An element is a
particular set of code that alters how the image is built, or runs within the
chroot to prepare the image.

The additional elements required by Sahara images and the ``sahara-image-create``
command itself are stored in the
`Sahara image elements repository <https://opendev.org/openstack/sahara-image-elements>`_

To create images for a specific plugin follow these steps:

1. Clone repository "https://opendev.org/openstack/sahara-image-elements"
   locally.

2. Use tox to build images.

   You can run the command below in sahara-image-elements
   directory to build images. By default this script will attempt to create
   cloud images for all versions of supported plugins and all operating systems
   (subset of Ubuntu, Fedora, and CentOS depending on plugin).

   .. sourcecode::

      tox -e venv -- sahara-image-create -u

   If you want to build a image for ``<plugin>`` with ``<version>`` on a specific
   ``<distribution>`` just execute:

   .. sourcecode::

      tox -e venv -- sahara-image-create -p <plugin> -v <version> -i <distribution>

   Tox will create a virtualenv and install required python packages in it,
   clone the repositories "https://opendev.org/openstack/diskimage-builder" and
   "https://opendev.org/openstack/sahara-image-elements" and export necessary
   parameters.

   The valid values for the ``<distribution>`` argument are:

   - Ubuntu (all versions): ``ubuntu``
   - CentOS 7: ``centos7``
   - Fedora: ``fedora``

   ``sahara-image-create`` will then create the required cloud images
   using image elements that install all the necessary packages
   and configure them.
   You will find created images in the parent directory.

Variables
~~~~~~~~~

The following environment variables can be used to change the behavior of the
image building:

* ``JAVA_DOWNLOAD_URL`` - download link for JDK (tarball or bin)
* ``DIB_IMAGE_SIZE`` - parameter that specifies a volume of hard disk
  of instance. You need to specify it only for Fedora because Fedora
  doesn't use all available volume

The following variables can be used to change the name of the output
image:

* ``centos7_image_name``
* ``ubuntu_image_name``
* ``fedora_image_name``

.. note::

    Disk Image Builder will generate QCOW2 images, used with the default
    OpenStack Qemu/KVM hypervisors. If your OpenStack uses a different
    hypervisor, the generated image should be converted to an appropriate
    format.

For finer control of ``sahara-image-create`` see the `official documentation
<https://opendev.org/openstack/sahara-image-elements/src/branch/master/diskimage-create/README.rst>`_
