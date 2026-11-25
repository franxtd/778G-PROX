### AnyKernel3 - Motorola Edge 30 (dubai)
## Based on osm0sis/AnyKernel3

properties() { '
kernel.string=FranProx Dubai LOS21 - BakaSU (experimental boot-only)
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=dubai
supported.versions=14
supported.patchlevels=
supported.vendorpatchlevels=
'; }

BLOCK=boot;
IS_SLOT_DEVICE=1;
SLOT_SELECT=active;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=0;

. tools/ak3-core.sh;

ui_print "Experimental boot-only package. Requires compatible ROM modules.";
split_boot;
flash_boot;
