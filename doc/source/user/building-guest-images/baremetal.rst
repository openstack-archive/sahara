.. _building-baremetal-images-label:

Bare metal images
-----------------

Images that can be used for bare metal deployment through Ironic
can be generated using both image building tools:

sahara-image-create:
  pass the -b parameters to the command

sahara-image-pack:
  use `virt-get-kernel` on the generated image to extract the kernel and
  the initramfs file
