-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: zlib
Binary: zlib1g, zlib1g-dev, zlib1g-udeb, lib64z1, lib64z1-dev, lib32z1, lib32z1-dev, libn32z1, libn32z1-dev, minizip, libminizip1t64, libminizip-dev
Architecture: any
Version: 1:1.3.dfsg+really1.3.1-1
Maintainer: Mark Brown <broonie@debian.org>
Homepage: http://zlib.net/
Standards-Version: 4.6.1
Build-Depends: dpkg-dev (>= 1.22.5), debhelper (>= 13), gcc-multilib [amd64 i386 kfreebsd-amd64 mips mipsel powerpc ppc64 s390 sparc s390x mipsn32 mipsn32el mipsr6 mipsr6el mipsn32r6 mipsn32r6el mips64 mips64el mips64r6 mips64r6el x32] <!nobiarch>, autoconf
Package-List:
 lib32z1 deb libs optional arch=amd64,ppc64,kfreebsd-amd64,s390x profile=!nobiarch
 lib32z1-dev deb libdevel optional arch=amd64,ppc64,kfreebsd-amd64,s390x profile=!nobiarch
 lib64z1 deb libs optional arch=sparc,s390,i386,powerpc,mips,mipsel,mipsn32,mipsn32el,mipsr6,mipsr6el,mipsn32r6,mipsn32r6el,x32 profile=!nobiarch
 lib64z1-dev deb libdevel optional arch=sparc,s390,i386,powerpc,mips,mipsel,mipsn32,mipsn32el,mipsr6,mipsr6el,mipsn32r6,mipsn32r6el,x32 profile=!nobiarch
 libminizip-dev deb libdevel optional arch=any
 libminizip1t64 deb libs optional arch=any
 libn32z1 deb libs optional arch=mips,mipsel profile=!nobiarch
 libn32z1-dev deb libdevel optional arch=mips,mipsel profile=!nobiarch
 minizip deb utils optional arch=any
 zlib1g deb libs required arch=any
 zlib1g-dev deb libdevel optional arch=any
 zlib1g-udeb udeb debian-installer optional arch=any
Checksums-Sha1:
 3b19b81105d3436095134a648c521b678905eaac 1325737 zlib_1.3.dfsg+really1.3.1.orig.tar.gz
 8b454f72def33b4a329489b8dcb2568ba0ccac69 16576 zlib_1.3.dfsg+really1.3.1-1.debian.tar.xz
Checksums-Sha256:
 60dd315c07f616887caa029408308a018ace66e3d142726a97db164b3b8f69fb 1325737 zlib_1.3.dfsg+really1.3.1.orig.tar.gz
 9ed525955ce9fb0c1b39be8ff98f73450dbfc6305a9a27e6149c8972d38a0a9e 16576 zlib_1.3.dfsg+really1.3.1-1.debian.tar.xz
Files:
 29e0750ce6c0a9f719354d678ebffc6e 1325737 zlib_1.3.dfsg+really1.3.1.orig.tar.gz
 1f978cc7b529a056788500a6cb84f8d6 16576 zlib_1.3.dfsg+really1.3.1-1.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQFHBAEBCgAxFiEEreZoqmdXGLWf4p/qJNaLcl1Uh9AFAmY9+y4THGJyb29uaWVA
ZGViaWFuLm9yZwAKCRAk1otyXVSH0J6+B/9H/d/qvCtMUEL0Z3v87R8JnH4hAARN
Ji4+cyJQbkF3PvXivx7+HsoNmEVInZDqfgnUMM8ENR1N03kWMlDM4wjFipGbv5i9
dziS5sYNjc9VfCIGykUMYYMkZgJIESWNlS+T0UC6nhGT5RUaH8uAMBQpRixtPL+L
AIxSS+WbGzcyN4PzFjJi7fo6CPr+0qd1hr95qF1hl2obLkeMC8f6I6EAFIZbTFph
26NPhZz6iTt3gaz33Vo9F03z2qmOuV5lFpAXYQhKTvGrnrs7cdw92kRGLj6J6Pg6
rG5DQDYua/06ZJqn9L010I3b2Pqg2dFwmYv3rs2Zmp4vmsay08JtSI/I
=CO8I
-----END PGP SIGNATURE-----
