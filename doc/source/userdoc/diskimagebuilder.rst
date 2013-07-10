Disk Image Builder
==================

As of now vanilla plugin works with images with pre-installed Apache Hadoop. To
simplify task of building such images we use
`Disk Image Builder <https://github.com/stackforge/diskimage-builder>`_.

`Disk Image Builder` is built of elements. An element is a particular set of
code that alters how the image is built, or runs within the chroot to prepare
the image.


.. note::

   Savanna requires images with cloud-init package installed:

   * `For Fedora <http://pkgs.fedoraproject.org/cgit/cloud-init.git/>`_
   * `For Ubuntu <http://packages.ubuntu.com/precise/cloud-init>`_

In this document you will find instuction on how to build Ubuntu and Fedora
images with Apache Hadoop 1.1.2.

1. Clone the repository "https://github.com/stackforge/diskimage-builder" locally.

   .. sourcecode:: concole

       git clone https://github.com/stackforge/diskimage-builder

2. Add ``~/diskimage-builder/bin/`` directory to your path. For example:

   .. sourcecode:: bash

       PATH=$PATH:/home/$USER/diskimage-builder/bin/.

3. Export the following variable
    ``ELEMENTS_PATH=/home/$USER/diskimage-builder/elements/``
    to your ``.bashrc``. Then source it.

4. Copy file ``img-build-sudoers`` from ``~/disk-image-builder/sudoers.d/``
   to your ``/etc/sudoers.d/``:

   .. sourcecode:: bash

       sudo cp ~/disk-image-builder/sudoers.d/img-build-sudoers /etc/sudoers.d/
       sudo chmod 440 /etc/sudoers.d/img-build-sudoers
       sudo chown root:root /etc/sudoers.d/img-build-sudoers

5. Move ``elements`` directory to ``disk-image-builder/elements/``

   .. sourcecode:: console

    mv elements/*  /path_to_disk_image_builder/diskimage-builder/elements/

6. Call the following command to create cloud image with Apache Hadoop:

   **Ubuntu cloud image**

   .. sourcecode:: console

       DIB_HADOOP_VERSION=1.1.2 JAVA_FILE=jdk-7u21-linux-x64.tar.gz \
           disk-image-create base vm hadoop ubuntu root-passwd -o hadoop_1_1_2

   **Fedora cloud image**

   .. sourcecode:: console

        DIB_HADOOP_VERSION=1.1.2 JAVA_FILE=jdk-7u21-linux-x64.tar.gz \
         DIB_IMAGE_SIZE=10 disk-image-create base vm fedora hadoop_fedora \
         root-passwd -o fedora_hadoop_1_1_2

   In this command:

   * ``DIB_HADOOP_VERSION`` - version of Hadoop to install (currently supports
     only Apache Hadoop 1.1.2)
   * ``JAVA_DOWNLOAD_URL`` - you also can use this parameter instead of
     ``DIB_HADOOP_VERSION`` to specify download link for JDK (tarball or bin)
   * ``DIB_IMAGE_SIZE`` - is parameter that specifes a volume of hard disk of
     instance. You need to specify it because Fedora doesn't use all available
     volume.

   If you have already downloaded the JDK package, move it to
   ``elements/hadoop/install.d/`` or ``elements/hadoop_fedora/post-install.d/``
   and use its filename as ``JAVA_FILE`` parameter.