.. _sahara-image-pack-label:

sahara-image-pack
-----------------

The CLI command ``sahara-image-pack`` operates in-place on an existing image
and installs and configures the software required for the plugin.

The script ``sahara-image-pack`` takes the following primary arguments:

::

  --config-file PATH    Path to a config file to use. Multiple config files
                        can be specified, with values in later files taking
                        precedence. Defaults to None.
  --image IMAGE         The path to an image to modify. This image will be
                        modified in-place: be sure to target a copy if you
                        wish to maintain a clean master image.
  --root-filesystem ROOT_FS
                        The filesystem to mount as the root volume on the
                        image. Novalue is required if only one filesystem is
                        detected.
  --test-only           If this flag is set, no changes will be made to the
                        image; instead, the script will fail if discrepancies
                        are found between the image and the intended state.

After these arguments, the script takes ``PLUGIN`` and ``VERSION`` arguments.
These arguments will allow any plugin and version combination which supports
the image packing feature. Plugins may require their own arguments at specific
versions; use the ``--help`` feature with ``PLUGIN`` and ``VERSION`` to see
the appropriate argument structure.


a plausible command-line invocation would be:

::

    sahara-image-pack --image CentOS.qcow2 \
        --config-file etc/sahara/sahara.conf \
        cdh 5.7.0 [cdh 5.7.0 specific arguments, if any]

This script will modify the target image in-place. Please copy your image
if you want a backup or if you wish to create multiple images from a single
base image.

This CLI will automatically populate the set of available plugins and
versions from the plugin set loaded in Sahara, and will show any plugin for
which the image packing feature is available. The next sections of this guide
will first describe how to modify an image packing specification for one
of the plugins, and second, how to enable the image packing feature for new
or existing plugins.

Note: In case of a RHEL 7 images, it is necessary to register the image before
starting to pack it, also enable some required repos.

::

    virt-customize -v -a $SAHARA_RHEL_IMAGE --sm-register \
        --sm-credentials ${REG_USER}:password:${REG_PASSWORD} --sm-attach \
        pool:${REG_POOL_ID} --run-command 'subscription-manager repos \
        --disable=* --enable=$REPO_A \ --enable=$REPO_B \ --enable=$REPO_C'

Installation and developer notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The script is part of the Sahara repository, but it does not depend
on the Sahara services. In order to use its development version,
clone the `Sahara repository <https://opendev.org/openstack/sahara>`_,
check out the branch which matches the Sahara version used, and
install the repository in a virtualenv.

The script is also provided by binary distributions of OpenStack.
For example, RDO ships it in the ``openstack-sahara-image-pack`` package.

The script depends on a python library which is not packaged
in pip, but is available through yum, dnf, and apt. If you have installed
Sahara through yum, dnf, or apt, you should have appropriate dependencies,
but if you wish to use the script but are working with Sahara from source,
run whichever of the following is appropriate to your OS:

::

    sudo yum install libguestfs python3-libguestfs libguestfs-tools
    sudo dnf install libguestfs python3-libguestfs libguestfs-tools
    sudo apt-get install libguestfs python3-guestfs libguestfs-tools

If you are using tox to create virtual environments for your Sahara work,
please use the ``images`` environment to run sahara-image-pack. This
environment is configured to use system site packages, and will thus
be able to find its dependency on python-libguestfs.
