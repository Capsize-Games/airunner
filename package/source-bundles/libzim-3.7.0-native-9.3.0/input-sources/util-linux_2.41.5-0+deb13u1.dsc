-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: util-linux
Binary: util-linux, util-linux-locales, mount, bsdutils, bsdextrautils, fdisk, fdisk-udeb, libblkid1, libblkid1-udeb, libblkid-dev, libfdisk1, libfdisk1-udeb, libfdisk-dev, libmount1, libmount1-udeb, libmount-dev, libsmartcols1, libsmartcols1-udeb, libsmartcols-dev, libuuid1, uuid-runtime, libuuid1-udeb, uuid-dev, util-linux-udeb, rfkill, eject, eject-udeb, util-linux-extra, liblastlog2-2, liblastlog2-dev, libpam-lastlog2, lastlog2, login
Architecture: any all
Version: 2.41.5-0+deb13u1
Maintainer: Chris Hofstaedtler <zeha@debian.org>
Homepage: https://github.com/util-linux/util-linux
Standards-Version: 4.7.0
Vcs-Browser: https://salsa.debian.org/debian/util-linux
Vcs-Git: https://salsa.debian.org/debian/util-linux.git
Testsuite: autopkgtest
Testsuite-Triggers: build-essential, expect, passwd, pkg-config
Build-Depends: debhelper-compat (= 13), dh-exec, dh-package-notes, dh-sequence-installsysusers, dh-sequence-zz-debputy-rrr (>= 0.1.23~), asciidoctor <!stage1 !nodoc>, bc <!stage1 !nocheck>, bison, flex, gettext, libaudit-dev [linux-any] <!stage1>, libcap-ng-dev [linux-any] <!stage1>, libcrypt-dev <!stage1>, libcryptsetup-dev [linux-any] <!pkg.util-linux.noverity>, libncurses-dev, libpam0g-dev <!stage1>, libreadline-dev, libselinux1-dev [linux-any], libsqlite3-dev, libsystemd-dev [linux-any] <!stage1>, libtool, libudev-dev [linux-any] <!stage1>, netbase <!stage1 !nocheck>, pkgconf, po-debconf, po4a, socat <!stage1 !nocheck>, systemd [linux-any] <!stage1>, systemd-dev [linux-any] <!stage1>, zlib1g-dev
Build-Conflicts: libedit-dev
Package-List:
 bsdextrautils deb utils optional arch=any profile=!stage1
 bsdutils deb utils required arch=any profile=!stage1 essential=yes
 eject deb utils optional arch=linux-any profile=!stage1
 eject-udeb udeb debian-installer optional arch=linux-any profile=!stage1,!noudeb
 fdisk deb utils important arch=any
 fdisk-udeb udeb debian-installer optional arch=hurd-any,linux-any profile=!stage1,!noudeb
 lastlog2 deb utils optional arch=any profile=!stage1
 libblkid-dev deb libdevel optional arch=any
 libblkid1 deb libs optional arch=any
 libblkid1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libfdisk-dev deb libdevel optional arch=any
 libfdisk1 deb libs optional arch=any
 libfdisk1-udeb udeb debian-installer optional arch=any profile=!noudeb
 liblastlog2-2 deb libs optional arch=any
 liblastlog2-dev deb libdevel optional arch=any
 libmount-dev deb libdevel optional arch=linux-any
 libmount1 deb libs optional arch=any
 libmount1-udeb udeb debian-installer optional arch=linux-any profile=!noudeb
 libpam-lastlog2 deb admin optional arch=any profile=!stage1
 libsmartcols-dev deb libdevel optional arch=any
 libsmartcols1 deb libs optional arch=any
 libsmartcols1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libuuid1 deb libs optional arch=any
 libuuid1-udeb udeb debian-installer optional arch=any profile=!noudeb
 login deb admin required arch=any profile=!stage1 protected=yes
 mount deb admin required arch=linux-any profile=!stage1
 rfkill deb utils optional arch=linux-any profile=!stage1
 util-linux deb utils required arch=any profile=!stage1 essential=yes
 util-linux-extra deb utils standard arch=any profile=!stage1
 util-linux-locales deb localization optional arch=all profile=!stage1
 util-linux-udeb udeb debian-installer optional arch=any profile=!stage1,!noudeb
 uuid-dev deb libdevel optional arch=any
 uuid-runtime deb utils optional arch=any profile=!stage1
Checksums-Sha1:
 aad638b4dea74be6227238f5e6398a8f54daefb4 9474992 util-linux_2.41.5.orig.tar.xz
 44d5f01ef357eca57a89f86125392fed89a8b14b 107604 util-linux_2.41.5-0+deb13u1.debian.tar.xz
Checksums-Sha256:
 f586e35d320ff537aab3ffeca37e9ecd482ccbe013590db4429a414d8aa6a728 9474992 util-linux_2.41.5.orig.tar.xz
 5b327ccd22f0f4ed28a389870aa51d04ecedb8693e52a1d122850f2b3188cbf6 107604 util-linux_2.41.5-0+deb13u1.debian.tar.xz
Files:
 c21a3cb29f510f019ac3da929819ffbf 9474992 util-linux_2.41.5.orig.tar.xz
 5265eba63ec6002d90959e435dedbac7 107604 util-linux_2.41.5-0+deb13u1.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEfRrP+tnggGycTNOSXBPW25MFLgMFAmpsxM0ACgkQXBPW25MF
LgMxwhAAlYC0HIImjeDEWj3gkao1iAU8MpT0rsf3aAwfc+uSrbPYG52vqKLikjYR
k8ZCpN1+XGMGO5HE7sh9U+y/S87hjM1AiM+IHuAg5z/rvzEmYrCBknZmsggjCG1N
PdGL9m7ri2KyKxxhuNJBIFjtiAm+G4jwXZ/x4MwjqtdjGyNtqOwlfRTZG4DCbSV6
UZKpNGZTlRsu8x9kiaUBKy8MHWbO9Gi/HOkI3DzWaWuPwLs+ziPQSQ6YutueI4Ei
C4Mya2T3aK6fmAnXhd6eKPATorEtvZTQNeTGFB93Yykerlc+FdnSWPqN+bv4CUpu
BuMwtS7PyCpSXPK8svfE2e2sZetCmIVkjs+XxORk3uQzZ3UP6ZEsZKG/MP+sSf9p
orVRqtNe0pAPFz8nCHr2Wke1A+zBUQqjpE6Jpm8r8pN+wNADV3tQAV2P/cJzN4NZ
iksLmaik/iAVP42PWAyU1G5KTUqyJ8NjGyNqytG1SI7oqb/kIacumHTtLMfImN6p
8HJqih+QBVpOqriuhjog8nZJjq/qSxVcVaevU770rh45DuSvFzXQhDFy5q5WgzsS
fR/3ugrJa0wPTr2xBWCSLjCZW75Z4dMUUX3ZM6eptFCXxOR8ZdVExfH5T9ct+3Le
HQXbMct4aqU/8yPkyRNviJ63G1Msc4IJv8b0qg2n4E93fDYaCyw=
=bFWO
-----END PGP SIGNATURE-----
