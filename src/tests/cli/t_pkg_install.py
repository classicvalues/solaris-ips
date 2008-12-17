#!/usr/bin/python2.4
#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at usr/src/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at usr/src/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
#

# Copyright 2008 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.

import testutils
if __name__ == "__main__":
        testutils.setup_environment("../../../proto")

import os
import re
import time
import unittest
import shutil
from stat import *

class TestPkgInstallBasics(testutils.SingleDepotTestCase):
        # Only start/stop the depot once (instead of for every test)
        persistent_depot = True

        foo10 = """
            open foo@1.0,5.11-0
            close """

        foo11 = """
            open foo@1.1,5.11-0
            add dir mode=0755 owner=root group=bin path=/lib
            add file /tmp/libc.so.1 mode=0555 owner=root group=bin path=/lib/libc.so.1 timestamp="20080731T024051Z"
            close """
        foo11_timestamp = 1217472051

        foo12 = """
            open foo@1.2,5.11-0
            add file /tmp/libc.so.1 mode=0555 owner=root group=bin path=/lib/libc.so.1
            close """

        bar10 = """
            open bar@1.0,5.11-0
            add depend type=require fmri=pkg:/foo@1.0
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/cat mode=0555 owner=root group=bin path=/bin/cat
            close """

        bar11 = """
            open bar@1.1,5.11-0
            add depend type=require fmri=pkg:/foo@1.2
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/cat mode=0555 owner=root group=bin path=/bin/cat
            close """

        xfoo10 = """
            open xfoo@1.0,5.11-0
            close """

        xbar10 = """
            open xbar@1.0,5.11-0
            add depend type=require fmri=pkg:/xfoo@1.0
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/cat mode=0555 owner=root group=bin path=/bin/cat
            close """

        xbar11 = """
            open xbar@1.1,5.11-0
            add depend type=require fmri=pkg:/xfoo@1.2
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/cat mode=0555 owner=root group=bin path=/bin/cat
            close """


        bar12 = """
            open bar@1.2,5.11-0
            add depend type=require fmri=pkg:/foo@1.0
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/cat mode=0555 owner=root group=bin path=/bin/cat 
            close """

        baz10 = """
            open baz@1.0,5.11-0
            add depend type=require fmri=pkg:/foo@1.0
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/baz mode=0555 owner=root group=bin path=/bin/baz
            close """

        deep10 = """
            open deep@1.0,5.11-0
            add depend type=require fmri=pkg:/bar@1.0
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/cat mode=0555 owner=root group=bin path=/bin/cat
            close """
        
        xdeep10 = """
            open xdeep@1.0,5.11-0
            add depend type=require fmri=pkg:/xbar@1.0
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/cat mode=0555 owner=root group=bin path=/bin/cat
            close """

        ydeep10 = """
            open ydeep@1.0,5.11-0
            add depend type=require fmri=pkg:/ybar@1.0
            add dir mode=0755 owner=root group=bin path=/bin
            add file /tmp/cat mode=0555 owner=root group=bin path=/bin/cat
            close """

        misc_files = [ "/tmp/libc.so.1", "/tmp/cat", "/tmp/baz" ]

        def setUp(self):
                testutils.SingleDepotTestCase.setUp(self)
                for p in self.misc_files:
                        f = open(p, "w")
                        # write the name of the file into the file, so that
                        # all files have differing contents
                        f.write(p)
                        f.close
                        self.debug("wrote %s" % p)

        def tearDown(self):
                testutils.SingleDepotTestCase.tearDown(self)
                for p in self.misc_files:
                        os.remove(p)

        def test_cli(self):
                """Test bad cli options"""

                durl = self.dc.get_depot_url()
                self.image_create(durl)

                self.pkg("-@", exit=2)
                self.pkg("-s status", exit=2)
                self.pkg("-R status", exit=2)

                self.pkg("install -@ foo", exit=2)
                self.pkg("install -vq foo", exit=2)
                self.pkg("install", exit=2)
                self.pkg("install foo@x.y", exit=1)
                self.pkg("install pkg:/foo@bar.baz", exit=1)

        def test_basics_1(self):
                """ Send empty package foo@1.0, install and uninstall """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.image_create(durl)

                self.pkg("list -a")
                self.pkg("list", exit=1)

                self.pkg("install foo")

                self.pkg("list")
                self.pkg("verify")

                self.pkg("uninstall foo")
                self.pkg("verify")


        def test_basics_2(self):
                """ Send package foo@1.1, containing a directory and a file,
                    install, search, and uninstall. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.pkg("list -a")
                self.pkg("install foo")
                self.pkg("verify")
                self.pkg("list")

                self.pkg("search /lib/libc.so.1")
                self.pkg("search -r /lib/libc.so.1")
                self.pkg("search blah", exit = 1)
                self.pkg("search -r blah", exit = 1)

                # check to make sure timestamp was set to correct value

                libc_path = os.path.join(self.get_img_path(), "lib/libc.so.1")
                stat = os.stat(libc_path)

                assert (stat[ST_MTIME] == self.foo11_timestamp)

                # check that verify finds changes
                now = time.time()
                os.utime(libc_path, (now, now))
                self.pkg("verify", exit=1)

                self.pkg("uninstall foo")
                self.pkg("verify")
                self.pkg("list -a")
                self.pkg("verify")


        def test_basics_3(self):
                """ Install foo@1.0, upgrade to foo@1.1, uninstall. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.pkg("install foo@1.0")
                self.pkg("list foo@1.0")
                self.pkg("list foo@1.1", exit = 1)

                self.pkg("install foo@1.1")
                self.pkg("list foo@1.1")
                self.pkg("list foo@1.0", exit = 1)
                self.pkg("list foo@1")
                self.pkg("verify")

                self.pkg("uninstall foo")
                self.pkg("list -a")
                self.pkg("verify")

        def test_basics_4(self):
                """ Add bar@1.0, dependent on foo@1.0, install, uninstall. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.pkgsend_bulk(durl, self.foo11)
                self.pkgsend_bulk(durl, self.bar10)
                self.image_create(durl)

                self.pkg("list -a")
                self.pkg("install bar@1.0")
                self.pkg("list")
                self.pkg("verify")
                self.pkg("uninstall -v bar foo")

                # foo and bar should not be installed at this point
                self.pkg("list bar", exit = 1)
                self.pkg("list foo", exit = 1)
                self.pkg("verify")

        def test_image_upgrade(self):
                """ Send package bar@1.1, dependent on foo@1.2.  Install bar@1.0.
                    List all packages.  Upgrade image. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.pkgsend_bulk(durl, self.foo11)
                self.pkgsend_bulk(durl, self.bar10)
                self.image_create(durl)

                self.pkg("install bar@1.0")

                self.pkgsend_bulk(durl, self.foo12)
                self.pkgsend_bulk(durl, self.bar11)

                self.pkg("contents -H")
                self.pkg("list")
                self.pkg("refresh")

                self.pkg("list")
                self.pkg("verify")
                self.pkg("image-update -v")
                self.pkg("verify")

                self.pkg("list foo@1.2")
                self.pkg("list bar@1.1")

                self.pkg("uninstall bar foo")
                self.pkg("verify")

        def test_recursive_uninstall(self):
                """Install bar@1.0, dependent on foo@1.0, uninstall foo recursively."""

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.pkgsend_bulk(durl, self.foo11)
                self.pkgsend_bulk(durl, self.bar10)
                self.image_create(durl)

                self.pkg("install bar@1.0")

                # Here's the real part of the regression test;
                # at this point foo and bar are installed, and
                # bar depends on foo.  foo and bar should both
                # be removed by this action.
                self.pkg("uninstall -vr foo")
                self.pkg("list bar", exit = 1)
                self.pkg("list foo", exit = 1)

        def test_nonrecursive_dependent_uninstall(self):
                """Trying to remove a package that's a dependency of another
                package should fail if the uninstall isn't recursive."""

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.pkgsend_bulk(durl, self.bar10)
                self.image_create(durl)

                self.pkg("install bar@1.0")

                self.pkg("uninstall -v foo", exit = 1)
                self.pkg("list bar")
                self.pkg("list foo")

        def test_basics_5(self):
                """ Add bar@1.1, install bar@1.0. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.xbar11)
                self.image_create(durl)

                self.pkg("install xbar@1.0", exit = 1)

        def test_bug_1338(self):
                """ Add bar@1.1, dependent on foo@1.2, install bar@1.1. """
                
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.bar11)
                self.image_create(durl)

                self.pkg("install bar@1.1", exit = 1)
                
        def test_bug_1338_2(self):
                """ Add bar@1.1, dependent on foo@1.2, and baz@1.0, dependent
                    on foo@1.0, install baz@1.0 and bar@1.1. """
                
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.bar11)
                self.pkgsend_bulk(durl, self.baz10)
                self.image_create(durl)

                self.pkg("install baz@1.0 bar@1.1", exit = 1)

        def test_bug_1338_3(self):
                """ Add xdeep@1.0, xbar@1.0. xDeep@1.0 depends on xbar@1.0 which
                    depends on xfoo@1.0, install xdeep@1.0. """
                
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.xbar10)
                self.pkgsend_bulk(durl, self.xdeep10)
                self.image_create(durl)

                self.pkg("install xdeep@1.0", exit = 1)

        def test_bug_1338_4(self):
                """ Add ydeep@1.0. yDeep@1.0 depends on ybar@1.0 which depends
                on xfoo@1.0, install ydeep@1.0. """
                
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.ydeep10)
                self.image_create(durl)

                self.pkg("install ydeep@1.0", exit = 1)

        def test_bug_2795(self):
                """ Try to install two versions of the same package """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.pkgsend_bulk(durl, self.foo12)
                self.image_create(durl)

                self.pkg("install foo@1.1 foo@1.2")
                self.pkg("list foo@1.1", exit = 1)
                self.pkg("list foo@1.2")
                self.pkg("uninstall foo")

                self.pkg("install foo@1.2 foo@1.1")
                self.pkg("list foo@1.1", exit = 1)
                self.pkg("list foo@1.2")
                

        def test_install_matching(self):
                """ Try to [un]install packages matching a pattern """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.pkgsend_bulk(durl, self.bar10)
                self.pkgsend_bulk(durl, self.baz10)
                self.image_create(durl)

                self.pkg("install 'ba*'")
                self.pkg("list foo@1.0", exit=0)
                self.pkg("list bar@1.0", exit=0)
                self.pkg("list baz@1.0", exit=0)

                self.pkg("uninstall 'ba*'")
                self.pkg("list foo@1.0", exit=0)
                self.pkg("list bar@1.0", exit=1)
                self.pkg("list baz@1.0", exit=1)

        def test_bug_3770(self):
                """ Try to install two versions of the same package """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)
                self.dc.stop()
                self.pkg("install foo@1.1", exit=1)
                self.dc.start()

        def test_bug_4204(self):
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo10)
                self.pkgsend_bulk(durl, self.bar10)
                self.image_create(durl)

                self.pkg("install foo")
                foo_dir = os.path.join(self.img_path, "var", "pkg", "pkg", "foo")
                old_ver = os.listdir(foo_dir)[0]
                new_ver = old_ver[:-2]+ str((int(old_ver[-2]) + 1) % 10) + \
                    old_ver[-1]
                shutil.copytree(os.path.join(foo_dir, old_ver),
                    os.path.join(foo_dir, new_ver))
                state_dir = os.path.join(self.img_path, "var", "pkg", "state",
                    "installed")
                shutil.copy(os.path.join(state_dir, "foo@" + old_ver),
                    os.path.join(state_dir, "foo@" + new_ver))
                cat_file = os.path.join(self.img_path, "var", "pkg", "catalog",
                    "catalog.pkl")
                os.unlink(cat_file)
                # Installing bar seems necessary to cause uninstall foo to fail.
                self.pkg("install bar")
                self.pkg("uninstall foo", exit=1)


class TestPkgInstallCircularDependencies(testutils.SingleDepotTestCase):
        # Only start/stop the depot once (instead of for every test)
        persistent_depot = True

        pkg10 = """
            open pkg1@1.0,5.11-0
            add depend type=require fmri=pkg:/pkg2
            close
        """

        pkg20 = """
            open pkg2@1.0,5.11-0
            add depend type=require fmri=pkg:/pkg3
            close
        """

        pkg30 = """
            open pkg3@1.0,5.11-0
            add depend type=require fmri=pkg:/pkg1
            close
        """


        pkg11 = """
            open pkg1@1.1,5.11-0
            add depend type=require fmri=pkg:/pkg2@1.1
            close
        """

        pkg21 = """
            open pkg2@1.1,5.11-0
            add depend type=require fmri=pkg:/pkg3@1.1
            close
        """

        pkg31 = """
            open pkg3@1.1,5.11-0
            add depend type=require fmri=pkg:/pkg1@1.1
            close
        """

        def test_unanchored_circular_dependencies(self):
                """ check to make sure we can install
                circular dependencies w/o versions
                """

                # Send 1.0 versions of packages.
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.pkg10)
                self.pkgsend_bulk(durl, self.pkg20)
                self.pkgsend_bulk(durl, self.pkg30)

                self.image_create(durl)
                self.pkg("install pkg1")
                self.pkg("list")
                self.pkg("verify -v")

        def test_anchored_circular_dependencies(self):
                """ check to make sure we can install
                circular dependencies w/ versions
                """

                # Send 1.0 versions of packages.
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.pkg11)
                self.pkgsend_bulk(durl, self.pkg21)
                self.pkgsend_bulk(durl, self.pkg31)

                self.image_create(durl)
                self.pkg("install pkg1")
                self.pkg("list")
                self.pkg("verify -v")

                        
class TestPkgInstallUpgrade(testutils.SingleDepotTestCase):
        # Only start/stop the depot once (instead of for every test)
        persistent_depot = True

        incorp10 = """
            open incorp@1.0,5.11-0
            add depend type=incorporate fmri=pkg:/amber@1.0
            add depend type=incorporate fmri=pkg:/bronze@1.0
            close
        """

        incorp20 = """
            open incorp@2.0,5.11-0
            add depend type=incorporate fmri=pkg:/amber@2.0
            add depend type=incorporate fmri=pkg:/bronze@2.0
            close
        """

        incorp30 = """
            open incorp@3.0,5.11-0
            add depend type=incorporate fmri=pkg:/amber@2.0
            close
        """

        incorpA = """
            open incorpA@1.0,5.11-0
            add depend type=incorporate fmri=pkg:/amber@1.0
            add depend type=incorporate fmri=pkg:/bronze@1.0
            close
        """

        incorpB =  """
            open incorpB@1.0,5.11-0
            add depend type=incorporate fmri=pkg:/amber@2.0
            add depend type=incorporate fmri=pkg:/bronze@2.0
            close
        """

        iridium10 = """
            open iridium@1.0,5.11-0
            add depend fmri=pkg:/amber@2.0 type=require
            close
        """
        amber10 = """
            open amber@1.0,5.11-0
            add dir mode=0755 owner=root group=bin path=/lib
            add dir mode=0755 owner=root group=bin path=/etc
            add file /tmp/libc.so.1 mode=0555 owner=root group=bin path=/lib/libc.so.1
            add link path=/lib/libc.symlink target=/lib/libc.so.1
            add hardlink path=/lib/libc.hardlink target=/lib/libc.so.1
            add file /tmp/amber1 mode=0444 owner=root group=bin path=/etc/amber1
            add file /tmp/amber2 mode=0444 owner=root group=bin path=/etc/amber2
            add license /tmp/copyright1 license=copyright
            close
        """

        brass10 = """
            open brass@1.0,5.11-0
            add depend fmri=pkg:/bronze type=require
            close
        """

        bronze10 = """
            open bronze@1.0,5.11-0
            add dir mode=0755 owner=root group=bin path=/usr
            add dir mode=0755 owner=root group=bin path=/usr/bin
            add file /tmp/sh mode=0555 owner=root group=bin path=/usr/bin/sh
            add link path=/usr/bin/jsh target=./sh
            add hardlink path=/lib/libc.bronze target=/lib/libc.so.1
            add file /tmp/bronze1 mode=0444 owner=root group=bin path=/etc/bronze1
            add file /tmp/bronze2 mode=0444 owner=root group=bin path=/etc/bronze2
            add file /tmp/bronzeA1 mode=0444 owner=root group=bin path=/A/B/C/D/E/F/bronzeA1
            add depend fmri=pkg:/amber@1.0 type=require
            add license /tmp/copyright2 license=copyright
            close
        """

        amber20 = """
            open amber@2.0,5.11-0
            add dir mode=0755 owner=root group=bin path=/usr
            add dir mode=0755 owner=root group=bin path=/usr/bin
            add file /tmp/libc.so.1 mode=0555 owner=root group=bin path=/lib/libc.so.1
            add link path=/lib/libc.symlink target=/lib/libc.so.1
            add hardlink path=/lib/libc.amber target=/lib/libc.bronze
            add hardlink path=/lib/libc.hardlink target=/lib/libc.so.1
            add file /tmp/amber1 mode=0444 owner=root group=bin path=/etc/amber1
            add file /tmp/amber2 mode=0444 owner=root group=bin path=/etc/bronze2
            add depend fmri=pkg:/bronze@2.0 type=require
            add license /tmp/copyright2 license=copyright
            close
        """

        bronze20 = """
            open bronze@2.0,5.11-0
            add dir mode=0755 owner=root group=bin path=/etc
            add dir mode=0755 owner=root group=bin path=/lib
            add file /tmp/sh mode=0555 owner=root group=bin path=/usr/bin/sh
            add file /tmp/libc.so.1 mode=0555 owner=root group=bin path=/lib/libc.bronze
            add link path=/usr/bin/jsh target=./sh
            add hardlink path=/lib/libc.bronze2.0.hardlink target=/lib/libc.so.1
            add file /tmp/bronze1 mode=0444 owner=root group=bin path=/etc/bronze1
            add file /tmp/bronze2 mode=0444 owner=root group=bin path=/etc/amber2
            add license /tmp/copyright3 license=copyright
            add file /tmp/bronzeA2 mode=0444 owner=root group=bin path=/A1/B2/C3/D4/E5/F6/bronzeA2
            add depend fmri=pkg:/amber@2.0 type=require
            close 
        """

        bronze30 = """
            open bronze@3.0,5.11-0
            add dir mode=0755 owner=root group=bin path=/etc
            add dir mode=0755 owner=root group=bin path=/lib
            add file /tmp/sh mode=0555 owner=root group=bin path=/usr/bin/sh
            add file /tmp/libc.so.1 mode=0555 owner=root group=bin path=/lib/libc.bronze
            add link path=/usr/bin/jsh target=./sh
            add hardlink path=/lib/libc.bronze2.0.hardlink target=/lib/libc.so.1
            add file /tmp/bronze1 mode=0444 owner=root group=bin path=/etc/bronze1
            add file /tmp/bronze2 mode=0444 owner=root group=bin path=/etc/amber2
            add license /tmp/copyright3 license=copyright
            add file /tmp/bronzeA2 mode=0444 owner=root group=bin path=/A1/B2/C3/D4/E5/F6/bronzeA2
            add depend fmri=pkg:/amber@2.0 type=require
            close 
        """


        gold10 = """
            open gold@1.0,5.11-0
            add file /tmp/config1 mode=0644 owner=root group=bin path=etc/config1 preserve=true
            close
        """

        gold20 = """
            open gold@2.0,5.11-0
            add file /tmp/config2 mode=0644 owner=root group=bin path=etc/config2 original_name="gold:etc/config1" preserve=true
            close
        """

        gold30 =  """
            open gold@3.0,5.11-0
            close
        """

        silver10  = """
            open silver@1.0,5.11-0
            close
        """

        silver20  = """
            open silver@2.0,5.11-0
            add file /tmp/config2 mode=0644 owner=root group=bin path=etc/config1 original_name="gold:etc/config1" preserve=true
            close
        """
        silver30  = """
            open silver@3.0,5.11-0
            add file /tmp/config2 mode=0644 owner=root group=bin path=etc/config2 original_name="gold:etc/config1" preserve=true
            close
        """



        iron10 = """
            open iron@1.0,5.11-0
            add dir mode=0755 owner=root group=bin path=etc
            add file /tmp/config1 mode=0644 owner=root group=bin path=etc/foo
            add hardlink path=etc/foo.link target=foo
            close
        """
        iron20 = """
            open iron@2.0,5.11-0
            add dir mode=0755 owner=root group=bin path=etc
            add file /tmp/config2 mode=0644 owner=root group=bin path=etc/foo
            add hardlink path=etc/foo.link target=foo
            close
        """

        concorp10 = """
            open concorp@1.0,5.11-0
            add depend type=incorporate fmri=pkg:/amber@2.0
            add depend type=incorporate fmri=pkg:/bronze@2.0
            close
        """


        misc_files = [ "/tmp/amber1", "/tmp/amber2",
                    "/tmp/bronzeA1",  "/tmp/bronzeA2",
                    "/tmp/bronze1", "/tmp/bronze2",
                    "/tmp/copyright1", "/tmp/copyright2",
                    "/tmp/copyright3", "/tmp/copyright4",
                    "/tmp/libc.so.1", "/tmp/sh", "/tmp/config1", "/tmp/config2"]

        def setUp(self):
                testutils.SingleDepotTestCase.setUp(self)
                for p in self.misc_files:
                        f = open(p, "w")
                        # write the name of the file into the file, so that
                        # all files have differing contents
                        f.write(p)
                        f.close()
                        self.debug("wrote %s" % p)
                
        def tearDown(self):
                testutils.SingleDepotTestCase.tearDown(self)
                for p in self.misc_files:
                        os.remove(p)

        def test_upgrade1(self):

                """ Upgrade torture test.
                    Send package amber@1.0, bronze1.0; install bronze1.0, which
                    should cause amber to also install.
                    Send 2.0 versions of packages which contains a lot of
                    complex transactions between amber and bronze, then do
                    an image-update, and try to check the results.
                """

                # Send 1.0 versions of packages.
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.incorp10)
                self.pkgsend_bulk(durl, self.amber10)
                self.pkgsend_bulk(durl, self.bronze10)

                #
                # In version 2.0, several things happen:
                #
                # Amber and Bronze swap a file with each other in both directions.
                # The dependency flips over (Amber now depends on Bronze)
                # Amber and Bronze swap ownership of various directories.
                #
                # Bronze's 1.0 hardlink to amber's libc goes away and is replaced
                # with a file of the same name.  Amber hardlinks to that.
                #
                self.pkgsend_bulk(durl, self.incorp20)
                self.pkgsend_bulk(durl, self.amber20)
                self.pkgsend_bulk(durl, self.bronze20)

                # create image and install version 1
                self.image_create(durl)
                self.pkg("install incorp@1.0")
                self.pkg("install bronze")

                self.pkg("list amber@1.0 bronze@1.0")
                self.pkg("verify -v")

                # demonstrate that incorp@1.0 prevents package movement
                self.pkg("install bronze@2.0 amber@2.0", exit=1)

                # Now image-update to get new versions of amber and bronze
                self.pkg("image-update")

                # Try to verify that it worked.
                self.pkg("list amber@2.0 bronze@2.0")
                self.pkg("verify -v")
                # make sure old implicit directories for bronzeA1 were removed
                self.assert_(not os.path.isdir(os.path.join(self.get_img_path(), "A")))                
                # Remove packages
                self.pkg("uninstall amber bronze")
                self.pkg("verify -v")

                # make sure all directories are gone save /var in test image
                self.assert_(os.listdir(self.get_img_path()) ==  ["var"])

        def test_upgrade2(self):
                """ test incorporations:
                        1) install files that conflict w/ existing incorps
                        2) install package w/ dependencies that violate incorps
                        3) install incorp that violates existing incorp
                        4) install incorp that would force package backwards
                        5) 
                        """

                # Send all pkgs
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.incorp10)
                self.pkgsend_bulk(durl, self.incorp20)
                self.pkgsend_bulk(durl, self.incorp30)
                self.pkgsend_bulk(durl, self.iridium10)
                self.pkgsend_bulk(durl, self.concorp10)
                self.pkgsend_bulk(durl, self.amber10)
                self.pkgsend_bulk(durl, self.amber20)
                self.pkgsend_bulk(durl, self.bronze10)
                self.pkgsend_bulk(durl, self.bronze20)
                self.pkgsend_bulk(durl, self.bronze30)
                self.pkgsend_bulk(durl, self.brass10)

                self.image_create(durl)

                self.pkg("install incorp@1.0")
                # install files that conflict w/ existing incorps
                self.pkg("install bronze@2.0", exit=1)
                # install package w/ dependencies that violate incorps
                self.pkg("install iridium@1.0", exit=1)
                # install package w/ unspecified dependency that pulls
                # in bronze
                self.pkg("install brass")
                self.pkg("verify brass@1.0 bronze@1.0")
                # attempt to install conflicting incorporation
                self.pkg("install concorp@1.0", exit=1)

                # attempt to force downgrade of package w/ older incorp
                self.pkg("install incorp@2.0")
                self.pkg("uninstall incorp@2.0")
                self.pkg("install incorp@1.0", exit=1)

                # upgrade pkg that loses incorp. deps. in new version
                self.pkg("install incorp@2.0")
                # FIX ME; bronze doesn't get updated because it was part
                # of previous incorporation
                self.pkg("image-update")
                self.pkg("list bronze@3.0", exit=1)

        def test_upgrade3(self):
                """ test for editable files moving between packages or locations or both"""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.silver10)
                self.pkgsend_bulk(durl, self.silver20)
                self.pkgsend_bulk(durl, self.silver30)
                self.pkgsend_bulk(durl, self.gold10)
                self.pkgsend_bulk(durl, self.gold20)
                self.pkgsend_bulk(durl, self.gold30)
              
                self.image_create(durl)

                # first test - move an editable file between packages
                
                self.pkg("install gold@1.0 silver@1.0")
                self.pkg("verify -v")
                
                # modify config file

                str = "this file has been modified 1"
                file_path = "etc/config1"
                self.file_append(file_path, str)

               # make sure /etc/config1 contains correct string
                self.file_contains(file_path, str)

                # update packages

                self.pkg("install gold@3.0 silver@2.0")
                self.pkg("verify -v")
                
                # make sure /etc/config1 contains still correct string
                self.file_contains(file_path, str)

                self.pkg("uninstall silver gold")

                # test file moving within package

                self.pkg("install gold@1.0")
                self.pkg("verify -v")
                
                # modify config file
                str = "this file has been modified test 2"                
                file_path = "etc/config1"
                self.file_append(file_path, str)
                        
                self.pkg("install gold@2.0")
                self.pkg("verify -v")

                 # make sure /etc/config2 contains correct string

                file_path = "etc/config2"
                self.file_contains(file_path, str)

                self.pkg("uninstall gold")
                self.pkg("verify -v")

                # test movement in filesystem and across packages
                
                self.pkg("install gold@1.0 silver@1.0")
                self.pkg("verify -v")

                # modify config file

                file_path = "etc/config1"
                str = "this file has been modified test 3"
                self.file_append(file_path, str)

                self.file_contains(file_path, str)

                self.pkg("install gold@3.0 silver@3.0")
                self.pkg("verify -v")
                 # make sure /etc/config2 now contains correct string
                file_path = "etc/config2"
                self.file_contains(file_path, str)

        def test_upgrade4(self):
                """ test to make sure hardlinks are correctly restored when file they point to is updated """
       
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.iron10)
                self.pkgsend_bulk(durl, self.iron20)
              
                self.image_create(durl)
                
                self.pkg("install iron@1.0")
                self.pkg("verify -v")
           
                self.pkg("install iron@2.0")
                self.pkg("verify -v")
           

        def file_append(self, path, string):
                file_path = os.path.join(self.get_img_path(), path)
                f = file(file_path, "a+")
                f.write("\n%s\n" % string)
                f.close

        def file_contains(self, path, string):
                file_path = os.path.join(self.get_img_path(), path)
                f = file(file_path)
                for line in f:
                        if string in line:
                                f.close()
                                break
                else:
                        f.close()
                        self.assert_(False, "File %s does not contain %s" % (path, string))


class TestPkgInstallActions(testutils.SingleDepotTestCase):
        # Only start/stop the depot once (instead of for every test)
        persistent_depot = True

        ftpusers_data = \
"""# ident      "@(#)ftpusers   1.6     06/11/21 SMI"
#
# List of users denied access to the FTP server, see ftpusers(4).
#
root
bin
sys
adm
"""
        group_data = \
"""root::0:
other::1:root
bin::2:root,daemon
sys::3:root,bin,adm
adm::4:root,daemon
"""
        passwd_data = \
"""root:x:0:0::/root:/usr/bin/bash
daemon:x:1:1::/:
bin:x:2:2::/usr/bin:
sys:x:3:3::/:
adm:x:4:4:Admin:/var/adm:
"""
        shadow_data = \
"""root:9EIfTNBp9elws:13817::::::
daemon:NP:6445::::::
bin:NP:6445::::::
sys:NP:6445::::::
adm:NP:6445::::::
"""

        cat_data = " "
        
        foo10 = """
            open foo@1.0,5.11-0
            close """

        only_attr10 = """
            open only_attr@1.0,5.11-0
            add set name=foo value=bar
            close """

        only_depend10 = """
            open only_depend@1.0,5.11-0
            add depend type=require fmri=foo@1.0,5.11-0
            close """

        only_directory10 = """
            open only_dir@1.0,5.11-0
            add dir mode=0755 owner=root group=bin path=/bin
            close """

        only_driver10 = """
            open only_driver@1.0,5.11-0
            add driver name=zerg devlink="type=ddi_pseudo;name=zerg\\t\D"
            close """

        only_group10 = """
            open only_group@1.0,5.11-0
            add group groupname=Kermit gid=28
            close """

        only_group_file10 = """
            open only_group_file@1.0,5.11-0
            add dir mode=0755 owner=root group=Kermit path=/export/home/Kermit
            close """

        only_hardlink10 = """
            open only_hardlink@1.0,5.11-0
            add hardlink path=/cat.hardlink target=/cat
            close """

        only_legacy10 = """
            open only_legacy@1.0,5.11-0
            add legacy arch=i386 category=system desc="GNU make - A utility used to build software (gmake) 3.81" hotline="Please contact your local service provider" name="gmake - GNU make" pkg=SUNWgmake vendor="Sun Microsystems, Inc." version=11.11.0,REV=2008.04.29.02.08
            close """

        only_link10 = """
            open only_link@1.0,5.11-0
            add link path=/link target=/tmp/cat
            close """

        only_user10 = """
            open only_user@1.0,5.11-0
            add user username=Kermit group=adm home-dir=/export/home/Kermit
            close """

        only_user_file10 = """
            open only_user_file@1.0,5.11-0
            add dir mode=0755 owner=Kermit group=adm path=/export/home/Kermit
            close """

        empty_data = ""
        
        misc_files = [ "empty", "ftpusers", "group", "passwd", "shadow", "cat" ]
 
        testdata_dir = None

        pkg_name_valid_chars = {
            "never": " `~!@#$%^&*()=[{]}\\|;:\",<>?",
            "always": "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "after-first": "_/-.+",
            "at-end": "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-.+",
        }

        def setUp(self):

                testutils.SingleDepotTestCase.setUp(self)
                tp = self.get_test_prefix()
                self.testdata_dir = os.path.join(tp, "testdata")
                os.mkdir(self.testdata_dir)


                self.only_file10 = """
                    open only_file@1.0,5.11-0
                    add file """ + self.testdata_dir + """/cat mode=0555 owner=root group=bin path=/cat
                    close """
                    
                self.only_license10 = """
                    open only_license@1.0,5.11-0
                    add license """ + self.testdata_dir + """/cat license=copyright
                    close """
                
                self.basics0 = """
                    open basics@1.0,5.11-0
                    add file """ + self.testdata_dir + """/passwd mode=0644 owner=root group=sys path=etc/passwd preserve=true
                    add file """ + self.testdata_dir + """/shadow mode=0400 owner=root group=sys path=etc/shadow preserve=true
                    add file """ + self.testdata_dir + """/group mode=0644 owner=root group=sys path=etc/group preserve=true
                    add file """ + self.testdata_dir + """/ftpusers mode=0644 owner=root group=sys path=etc/ftpd/ftpusers preserve=true
                    add file """ + self.testdata_dir + """/empty mode=0644 owner=root group=sys path=etc/name_to_major preserve=true
                    add file """ + self.testdata_dir + """/empty mode=0644 owner=root group=sys path=etc/driver_aliases preserve=true
                    add dir mode=0755 owner=root group=bin path=/lib
                    add dir mode=0755 owner=root group=sys path=/etc
                    add dir mode=0755 owner=root group=sys path=/etc/ftpd
                    add dir mode=0755 owner=root group=sys path=/var
                    add dir mode=0755 owner=root group=sys path=/var/svc
                    add dir mode=0755 owner=root group=sys path=/var/svc/manifest
                    add dir mode=0755 owner=root group=bin path=/usr
                    add dir mode=0755 owner=root group=bin path=/usr/local
                    close """

                self.grouptest = """
                    open grouptest@1.0,5.11-0
                    add dir mode=0755 owner=root group=Kermit path=/usr/Kermit
                    add file """ + self.testdata_dir + """/empty mode=0755 owner=root group=Kermit path=/usr/local/bin/do_group_nothing
                    add group groupname=lp gid=8
                    add group groupname=staff gid=10
                    add group groupname=Kermit
                    add depend fmri=pkg:/basics@1.0 type=require
                    close """

                self.usertest10 = """
                    open usertest@1.0,5.11-0
                    add dir mode=0755 owner=Kermit group=Kermit path=/export/home/Kermit
                    add file """ + self.testdata_dir + """/empty mode=0755 owner=Kermit group=Kermit path=/usr/local/bin/do_user_nothing
                    add depend fmri=pkg:/basics@1.0 type=require
                    add user username=Kermit group=Kermit home-dir=/export/home/Kermit group-list=lp group-list=staff
                    add depend fmri=pkg:/grouptest@1.0 type=require
                    add depend fmri=pkg:/basics@1.0 type=require
                    close """

                self.usertest11 = """
                    open usertest@1.1,5.11-0
                    add dir mode=0755 owner=Kermit group=Kermit path=/export/home/Kermit
                    add file """ + self.testdata_dir + """/empty mode=0755 owner=Kermit group=Kermit path=/usr/local/bin/do_user_nothing
                    add depend fmri=pkg:/basics@1.0 type=require
                    add user username=Kermit group=Kermit home-dir=/export/home/Kermit group-list=lp group-list=staff group-list=root ftpuser=false
                    add depend fmri=pkg:/grouptest@1.0 type=require
                    add depend fmri=pkg:/basics@1.0 type=require
                    close """

                self.ugidtest = """
                    open ugidtest@1.0,5.11-0
                    add user username=dummy group=root
                    add group groupname=dummy
                    close """

                self.silver10 = """
                    open silver@1.0,5.11-0
                    add file """ + self.testdata_dir + """/empty mode=0755 owner=root group=root path=/usr/local/bin/silver
                    add depend fmri=pkg:/basics@1.0 type=require
                    close """
                self.silver20 = """
                    open silver@2.0,5.11-0
                    add file """ + self.testdata_dir + """/empty mode=0755 owner=Kermit group=Kermit path=/usr/local/bin/silver
                    add user username=Kermit group=Kermit home-dir=/export/home/Kermit group-list=lp group-list=staff
                    add depend fmri=pkg:/basics@1.0 type=require
                    add depend fmri=pkg:/grouptest@1.0 type=require
                    close """

                self.devicebase = """
                    open devicebase@1.0,5.11-0
                    add dir mode=0755 owner=root group=root path=/tmp
                    add dir mode=0755 owner=root group=root path=/etc
                    add dir mode=0755 owner=root group=root path=/etc/security
                    add file """ + self.testdata_dir + """/empty mode=0600 owner=root group=root path=/etc/devlink.tab preserve=true
                    add file """ + self.testdata_dir + """/empty mode=0644 owner=root group=sys path=/etc/name_to_major preserve=true
                    add file """ + self.testdata_dir + """/empty mode=0644 owner=root group=sys path=/etc/driver_aliases preserve=true
                    add file """ + self.testdata_dir + """/empty mode=0644 owner=root group=sys path=/etc/driver_classes preserve=true
                    add file """ + self.testdata_dir + """/empty mode=0644 owner=root group=sys path=/etc/minor_perm preserve=true
                    add file """ + self.testdata_dir + """/empty mode=0644 owner=root group=root path=/etc/security/device_policy preserve=true
                    add file """ + self.testdata_dir + """/empty mode=0644 owner=root group=sys path=/etc/security/extra_privs preserve=true
                    close
                """

                self.devlink10 = """
                    open devlinktest@1.0,5.11-0
                    add driver name=zerg devlink="type=ddi_pseudo;name=zerg\\t\D"
                    add driver name=borg devlink="type=ddi_pseudo;name=borg\\t\D" devlink="type=ddi_pseudo;name=warg\\t\D"
                    add depend type=require fmri=devicebase
                    close
                """

                self.devlink20 = """
                    open devlinktest@2.0,5.11-0
                    add driver name=zerg devlink="type=ddi_pseudo;name=zerg2\\t\D" devlink="type=ddi_pseudo;name=zorg\\t\D"
                    add driver name=borg devlink="type=ddi_pseudo;name=borg\\t\D" devlink="type=ddi_pseudo;name=zork\\t\D"
                    add depend type=require fmri=devicebase
                    close
                """

                for f in self.misc_files:
                        filename = os.path.join(self.testdata_dir, f)
                        file_handle = open(filename, 'wb')
                        try:
                                file_handle.write(eval("self.%s_data" % f))
                        finally:
                                file_handle.close()

        def tearDown(self):
                testutils.SingleDepotTestCase.tearDown(self)
                if self.testdata_dir:
                        shutil.rmtree(self.testdata_dir)
        
        def test_basics_0(self):
                """Send basic infrastructure, install and uninstall."""

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.basics0)
                self.image_create(durl)

                self.pkg("list -a")
                self.pkg("list", exit=1)

                self.pkg("install basics")

                self.pkg("list")
                self.pkg("verify")

                self.pkg("uninstall basics")
                self.pkg("verify")

        def test_grouptest(self):
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.basics0)
                self.pkgsend_bulk(durl, self.grouptest)
                self.image_create(durl)
                self.pkg("install basics")

                self.pkg("install grouptest")
                self.pkg("verify")
                self.pkg("uninstall grouptest")
                self.pkg("verify")

        def test_usertest(self):
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.basics0)
                self.pkgsend_bulk(durl, self.grouptest)
                self.pkgsend_bulk(durl, self.usertest10)
                self.image_create(durl)
                self.pkg("install basics")

                self.pkg("install usertest")
                self.pkg("verify")
                self.pkg("contents -m usertest")

                self.pkgsend_bulk(durl, self.usertest11)
                self.pkg("install usertest")
                self.pkg("verify")
                self.pkg("contents -m usertest")

                self.pkg("uninstall usertest")
                self.pkg("verify")

        def test_minugid(self):
                """Ensure that an unspecified uid/gid results in the first
                unused."""

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.ugidtest)
                self.image_create(durl)

                os.mkdir(os.path.join(self.get_img_path(), "etc"))
                os.mkdir(os.path.join(self.get_img_path(), "etc/ftpd"))
                for f in self.misc_files:
                        dir = "etc"
                        if f == "ftpusers":
                                dir = "etc/ftpd"
                        filename = os.path.join(self.get_img_path(), dir, f)
                        file_handle = open(filename, 'wb')
                        exec("%s_path = \"%s\"" % (f, filename))
                        try:
                                file_handle.write(eval("self.%s_data" % f))
                        finally:
                                file_handle.close()

                self.pkg("install ugidtest")
                passwd_file = file(passwd_path)
                for line in passwd_file:
                        if line.startswith("dummy"):
                                self.assert_(line.startswith("dummy:x:5:"))
                passwd_file.close()
                group_file = file(group_path)
                for line in group_file:
                        if line.startswith("dummy"):
                                self.assert_(line.startswith("dummy::5:"))
                group_file.close()

        def test_upgrade_with_user(self):
                """Ensure that we can add a user and change file ownership to
                that user in the same delta (mysql tripped over this early on
                in IPS development)."""
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.basics0)
                self.pkgsend_bulk(durl, self.silver10)
                self.pkgsend_bulk(durl, self.silver20)
                self.pkgsend_bulk(durl, self.grouptest)
                self.image_create(durl)
                self.pkg("install silver@1.0")
                self.pkg("list silver@1.0")
                self.pkg("verify -v")
                self.pkg("install silver@2.0")
                self.pkg("verify -v")

        def test_invalid_open(self):
                """Send a invalid package definition (invalid fmri); expect
                failure."""

                durl = self.dc.get_depot_url()

                for char in self.pkg_name_valid_chars["never"]:
                        invalid_name = "invalid%spkg@1.0,5.11-0" % char
                        self.pkgsend(durl, "open '%s'" % invalid_name, exit=1)

                for char in self.pkg_name_valid_chars["after-first"]:
                        invalid_name = "%sinvalidpkg@1.0,5.11-0" % char
                        if char == "-":
                                cmd = "open -- '%s'" % invalid_name
                        else:
                                cmd = "open '%s'" % invalid_name
                        self.pkgsend(durl, cmd, exit=1)

                        invalid_name = "invalid/%spkg@1.0,5.11-0" % char
                        cmd = "open '%s'" % invalid_name
                        self.pkgsend(durl, cmd, exit=1)

        def test_valid_open(self):
                """Send a invalid package definition (valid fmri); expect
                success."""

                durl = self.dc.get_depot_url()
                for char in self.pkg_name_valid_chars["always"]:
                        valid_name = "%svalid%s/%spkg%s@1.0,5.11-0" % (char,
                            char, char, char)
                        self.pkgsend(durl, "open '%s'" % valid_name)
                        self.pkgsend(durl, "close -A")

                for char in self.pkg_name_valid_chars["after-first"]:
                        valid_name = "v%salid%spkg@1.0,5.11-0" % (char, char)
                        self.pkgsend(durl, "open '%s'" % valid_name)
                        self.pkgsend(durl, "close -A")

                for char in self.pkg_name_valid_chars["at-end"]:
                        valid_name = "validpkg%s@1.0,5.11-0" % char
                        self.pkgsend(durl, "open '%s'" % valid_name)
                        self.pkgsend(durl, "close -A")

        def test_devlink(self):
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.devicebase)
                self.pkgsend_bulk(durl, self.devlink10)
                self.pkgsend_bulk(durl, self.devlink20)
                self.image_create(durl)

                def readfile():
                        dlf = file(os.path.join(self.get_img_path(),
                            "etc/devlink.tab"))
                        dllines = dlf.readlines()
                        dlf.close()
                        return dllines

                def writefile(dllines):
                        dlf = file(os.path.join(self.get_img_path(),
                            "etc/devlink.tab"), "w")
                        dlf.writelines(dllines)
                        dlf.close()

                def assertContents(dllines, contents):
                        actual = re.findall("name=([^\t;]*)",
                            "\n".join(dllines), re.M)
                        self.assert_(set(actual) == set(contents))

                # Install
                self.pkg("install devlinktest@1.0")
                self.pkg("verify -v")

                dllines = readfile()

                # Verify that three entries got added
                self.assert_(len(dllines) == 3)

                # Verify that the tab character got written correctly
                self.assert_(dllines[0].find("\t") > 0)

                # Upgrade
                self.pkg("install devlinktest@2.0")
                self.pkg("verify -v")

                dllines = readfile()

                # Verify that there are four entries now
                self.assert_(len(dllines) == 4)

                # Verify they are what they should be
                assertContents(dllines, ["zerg2", "zorg", "borg", "zork"])

                # Remove
                self.pkg("uninstall devlinktest")
                self.pkg("verify -v")

                # Install again
                self.pkg("install devlinktest@1.0")

                # Diddle with it
                dllines = readfile()
                for i, line in enumerate(dllines):
                        if line.find("zerg") != -1:
                                dllines[i] = "type=ddi_pseudo;name=zippy\t\D\n"
                writefile(dllines)

                # Upgrade
                self.pkg("install devlinktest@2.0")

                # Verify that we spewed a message on upgrade
                self.assert_(self.output.find("not found") != -1)
                self.assert_(self.output.find("name=zerg") != -1)

                # Verify the new set
                dllines = readfile()
                self.assert_(len(dllines) == 5)
                assertContents(dllines,
                    ["zerg2", "zorg", "borg", "zork", "zippy"])

                self.pkg("uninstall devlinktest")

                # Null out the "zippy" entry
                writefile([])

                # Install again
                self.pkg("install devlinktest@1.0")

                # Diddle with it
                dllines = readfile()
                for i, line in enumerate(dllines):
                        if line.find("zerg") != -1:
                                dllines[i] = "type=ddi_pseudo;name=zippy\t\D\n"
                writefile(dllines)

                # Remove
                self.pkg("uninstall devlinktest")

                # Verify that we spewed a message on removal
                self.assert_(self.output.find("not found") != -1)
                self.assert_(self.output.find("name=zerg") != -1)

                # Verify that the one left behind was the one we overwrote.
                dllines = readfile()
                self.assert_(len(dllines) == 1)
                assertContents(dllines, ["zippy"])

                # Null out the "zippy" entry, but add the "zerg" entry
                writefile(["type=ddi_pseudo;name=zerg\t\D\n"])

                # Install ... again
                self.pkg("install devlinktest@1.0")

                # Make sure we didn't get a second zerg line
                dllines = readfile()
                self.failUnless(len(dllines) == 3, msg=dllines)
                assertContents(dllines, ["zerg", "borg", "warg"])

                # Now for the same test on upgrade
                dllines.append("type=ddi_pseudo;name=zorg\t\D\n")
                writefile(dllines)

                self.pkg("install devlinktest@2.0")
                dllines = readfile()
                self.failUnless(len(dllines) == 4, msg=dllines)
                assertContents(dllines, ["zerg2", "zorg", "borg", "zork"])

        def test_uninstall_without_perms(self):
                """Test for bug 4569"""
                durl = self.dc.get_depot_url()

                pkg_list = [self.foo10, self.only_attr10, self.only_depend10,
                    self.only_directory10, self.only_driver10, self.only_file10,
                    self.only_group10, self.only_hardlink10, self.only_legacy10,
                    self.only_license10, self.only_link10, self.only_user10]
                
                for p in pkg_list:
                        self.pkgsend_bulk(durl, p)
                self.pkgsend_bulk(durl, self.devicebase)
                self.pkgsend_bulk(durl, self.basics0)

                self.image_create(durl)

                name_pat = re.compile("^\s+open\s+(\S+)\@.*$")

                def __manually_check_deps(name, install=True):
                        cmd = "install --no-refresh"
                        if not install:
                                cmd = "uninstall"
                        if name == "only_depend" and not install:
                                self.pkg("uninstall foo")
                        elif name == "only_driver":
                                self.pkg("%s devicebase" % cmd)
                        elif name == "only_group":
                                self.pkg("%s basics" % cmd)
                        elif name == "only_hardlink":
                                self.pkg("%s only_file" % cmd)
                        elif name == "only_user":
                                if install:
                                        self.pkg("%s basics" % cmd)
                                        self.pkg("%s only_group" % cmd)
                                else:
                                        self.pkg("%s only_group" % cmd)
                                        self.pkg("%s basics" % cmd)
                for p in pkg_list:
                        name_mat = name_pat.match(p.splitlines()[1])
                        pname = name_mat.group(1)
                        __manually_check_deps(pname)
                        self.pkg("install --no-refresh %s" % pname,
                            su_wrap="noaccess", exit=1)
                        self.pkg("install %s" % pname, su_wrap="noaccess",
                            exit=1)
                        self.pkg("install --no-refresh %s" % pname)
                        self.pkg("uninstall %s" % pname, su_wrap="noaccess",
                            exit=1)
                        self.pkg("uninstall %s" % pname)
                        __manually_check_deps(pname, install=False)

                for p in pkg_list:
                        name_mat = name_pat.match(p.splitlines()[1])
                        pname = name_mat.group(1)
                        __manually_check_deps(pname)
                        self.pkg("install --no-refresh %s" % pname)

                for p in pkg_list:
                        self.pkgsend_bulk(durl, p)
                self.pkgsend_bulk(durl, self.devicebase)
                self.pkgsend_bulk(durl, self.basics0)

                self.pkg("image-update --no-refresh", su_wrap="noaccess")
                self.pkg("image-update", su_wrap="noaccess", exit=1)
                self.pkg("refresh", su_wrap="noaccess", exit=1)
                self.pkg("refresh")
                self.pkg("image-update --no-refresh", su_wrap="noaccess",
                    exit=1)
                self.pkg("image-update")

        def test_bug_3222(self):
                """ Verify that a timestamp of '0' for a passwd file will not
                    cause further package operations to fail.  This can happen
                    when there are time synchronization issues within a virtual
                    environment or in other cases. """
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.basics0)
                self.pkgsend_bulk(durl, self.only_user10)
                self.pkgsend_bulk(durl, self.only_user_file10)
                self.pkgsend_bulk(durl, self.only_group10)
                self.pkgsend_bulk(durl, self.only_group_file10)
                self.pkgsend_bulk(durl, self.grouptest)
                self.pkgsend_bulk(durl, self.usertest10)
                self.image_create(durl)
                fname = os.path.join(self.get_img_path(), "etc", "passwd")
                self.pkg("install basics")

                # This should work regardless of whether a user is installed
                # at the same time as the file in a package, or if the user is
                # installed first and then files owned by that user are
                # installed.
                plists = [["grouptest", "usertest"],
                    ["only_user", "only_user_file"],
                    ["only_group", "only_group_file"]]
                for plist in plists:
                        for pname in plist:
                                os.utime(fname, (0, 0))
                                self.pkg("install %s" % pname)
                                self.pkg("verify")

                        for pname in reversed(plist):
                                os.utime(fname, (0, 0))
                                self.pkg("uninstall %s" % pname)
                                self.pkg("verify")

class TestDependencies(testutils.SingleDepotTestCase):
        # Only start/stop the depot once (instead of for every test)
        persistent_depot = True

        pkg10 = """
            open pkg1@1.0,5.11-0
            add depend type=optional fmri=pkg:/pkg2
            close
        """

        pkg20 = """
            open pkg2@1.0,5.11-0
            close
        """

        pkg11 = """
            open pkg1@1.1,5.11-0
            add depend type=optional fmri=pkg:/pkg2@1.1
            close
        """

        pkg21 = """
            open pkg2@1.1,5.11-0
            close
        """

        def setUp(self):
                testutils.SingleDepotTestCase.setUp(self)
                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.pkg10)
                self.pkgsend_bulk(durl, self.pkg20)
                self.pkgsend_bulk(durl, self.pkg11)
                self.pkgsend_bulk(durl, self.pkg21)

        def test_optional_dependencies(self):
                """ check to make sure that optional dependencies are enforced
                """

                durl = self.dc.get_depot_url()
                self.image_create(durl)
                self.pkg("install pkg1@1.0")

                # pkg2 is optional, it should not have been installed
                self.pkg("list pkg2", exit=1)

                self.pkg("install pkg2@1.0")

                # this should install pkg1 and upgrade pkg2 to pkg2@1.1
                self.pkg("install pkg1")
                self.pkg("list pkg2@1.1")

                self.pkg("uninstall pkg2")
                self.pkg("list pkg2", exit=1)
                # this should install pkg2@1.1 because of the optional 
                # dependency in pkg1
                self.pkg("install pkg2@1.0")
                self.pkg("list pkg2@1.1")

        def test_require_optional(self):
                """ check that the require optional policy is working
                """

                durl = self.dc.get_depot_url()
                self.image_create(durl)
                self.pkg("set-property require-optional true")
                self.pkg("install pkg1")
                # the optional dependency should be installed because of the
                # policy setting
                self.pkg("list pkg2@1.1")

class TestTwoDepots(testutils.ManyDepotTestCase):
        # Only start/stop the depot once (instead of for every test)
        persistent_depot = True

        foo10 = """
            open foo@1.0,5.11-0
            close """

        bar10 = """
            open bar@1.0,5.11-0
            close """

        moo10 = """
            open moo@1.0,5.11-0
            close """

        quux10 = """
            open quux@1.0,5.11-0
            add depend type=optional fmri=optional@1.0
            close"""

        optional10 = """
            open optional@1.0,5.11-0
            close"""

        upgrade_p10 = """
            open upgrade-p@1.0,5.11-0
            close"""

        upgrade_p11 = """
            open upgrade-p@1.1,5.11-0
            close"""

        upgrade_np10 = """
            open upgrade-np@1.0,5.11-0
            close"""

        upgrade_np11 = """
            open upgrade-np@1.1,5.11-0
            close"""

        incorp_p10 = """
            open incorp-p@1.0,5.11-0
            add depend type=incorporate fmri=upgrade-p@1.0
            close"""

        incorp_p11 = """
            open incorp-p@1.1,5.11-0
            add depend type=incorporate fmri=upgrade-p@1.1
            close"""

        incorp_np10 = """
            open incorp-np@1.0,5.11-0
            add depend type=incorporate fmri=upgrade-np@1.0
            close"""

        incorp_np11 = """
            open incorp-np@1.1,5.11-0
            add depend type=incorporate fmri=upgrade-np@1.1
            close"""

        def setUp(self):
                """ Start two depots.
                    depot 1 gets foo and moo, depot 2 gets foo and bar
                    depot1 is mapped to authority test1 (preferred)
                    depot2 is mapped to authority test2 """

                testutils.ManyDepotTestCase.setUp(self, 2)

                durl1 = self.dcs[1].get_depot_url()
                self.pkgsend_bulk(durl1, self.foo10)
                self.pkgsend_bulk(durl1, self.moo10)
                self.pkgsend_bulk(durl1, self.quux10)
                self.pkgsend_bulk(durl1, self.optional10)
                self.pkgsend_bulk(durl1, self.upgrade_p10)
                self.pkgsend_bulk(durl1, self.upgrade_np11)
                self.pkgsend_bulk(durl1, self.incorp_p10)
                self.pkgsend_bulk(durl1, self.incorp_p11)
                self.pkgsend_bulk(durl1, self.incorp_np10)
                self.pkgsend_bulk(durl1, self.incorp_np11)

                durl2 = self.dcs[2].get_depot_url()
                self.pkgsend_bulk(durl2, self.foo10)
                self.pkgsend_bulk(durl2, self.bar10)
                self.pkgsend_bulk(durl2, self.upgrade_p11)
                self.pkgsend_bulk(durl2, self.upgrade_np10)

                # Create image and hence primary authority
                self.image_create(durl1, prefix="test1")

                # Create second authority using depot #2
                self.pkg("set-authority -O " + durl2 + " test2")

        def tearDown(self):
                testutils.ManyDepotTestCase.tearDown(self)

        def test_basics_1(self):
                self.pkg("list -a")

                # Install and uninstall moo (which is unique to depot 1)
                self.pkg("install moo")

                self.pkg("list")
                self.pkg("uninstall moo")

                # Install and uninstall bar (which is unique to depot 2)
                self.pkg("install bar")

                self.pkg("list")

                self.pkg("uninstall bar")

                # Install and uninstall foo (which is in both depots)
                # In this case, we should select foo from depot 1, since
                # it is preferred.
                self.pkg("install foo")

                self.pkg("list pkg://test1/foo")

                self.pkg("uninstall foo")

        def test_basics_2(self):
                """ Test install from an explicit preferred authority """
                self.pkg("install pkg://test1/foo")
                self.pkg("list foo")
                self.pkg("list pkg://test1/foo")
                self.pkg("uninstall foo")

        def test_basics_3(self):
                """ Test install from an explicit non-preferred authority """
                self.pkg("install pkg://test2/foo")
                self.pkg("list foo")
                self.pkg("list pkg://test2/foo")
                self.pkg("uninstall foo")

        def test_upgrade_preferred_to_non_preferred(self):
                """Install a package from the preferred authority, and then
                upgrade it, implicitly switching to a non-preferred
                authority."""
                self.pkg("list -a upgrade-p")
                self.pkg("install upgrade-p@1.0")
                self.pkg("install upgrade-p@1.1")
                self.pkg("uninstall upgrade-p")

        def test_upgrade_non_preferred_to_preferred(self):
                """Install a package from a non-preferred authority, and then
                upgrade it, implicitly switching to the preferred authority."""
                self.pkg("list -a upgrade-np")
                self.pkg("install upgrade-np@1.0")
                self.pkg("install upgrade-np@1.1")
                self.pkg("uninstall upgrade-np")

        def test_upgrade_preferred_to_non_preferred_incorporated(self):
                """Install a package from the preferred authority, and then
                upgrade it, implicitly switching to a non-preferred
                authority, when the package is constrained by an
                incorporation."""
                self.pkg("list -a upgrade-p incorp-p")
                self.pkg("install incorp-p@1.0")
                self.pkg("install upgrade-p")
                self.pkg("install incorp-p@1.1")
                self.pkg("list upgrade-p@1.1")
                self.pkg("uninstall upgrade-p")

        def test_upgrade_non_preferred_to_preferred_incorporated(self):
                """Install a package from the preferred authority, and then
                upgrade it, implicitly switching to a non-preferred
                authority, when the package is constrained by an
                incorporation."""
                self.pkg("list -a upgrade-np incorp-np")
                self.pkg("install incorp-np@1.0")
                self.pkg("install upgrade-np")
                self.pkg("install incorp-np@1.1")
                self.pkg("list upgrade-np@1.1")
                self.pkg("uninstall upgrade-np")

        def test_uninstall_from_wrong_authority(self):
                """Install a package from an authority and try to remove it
                using a different authority name; this should fail."""
                self.pkg("install foo")
                self.pkg("uninstall pkg://test2/foo", exit=1)
                # Check to make sure that uninstalling using the explicit
                # authority works
                self.pkg("uninstall pkg://test1/foo")

        def test_yyy_install_after_authority_removal(self):
                """Install a package from an authority that has an optional
                dependency; then change the preferred authority and remove the
                original authority and attempt to uninstall the package."""
                self.pkg("install quux@1.0")
                self.pkg("set-authority -P test2")
                self.pkg("unset-authority test1")
                # 
                # 
                self.pkg("install quux@1.0")
                # Image update should work if we don't see the optional dependency
                self.pkg("image-update") 
                # Change the image metadata back to where it was, in preparation
                # for subsequent tests.
                self.pkg("set-authority -O %s -P test1" % \
                    self.dcs[1].get_depot_url())

        def test_zzz_uninstall_after_preferred_authority_change(self):
                """Install a package from the preferred authority, change the
                preferred authority, and attempt to remove the package."""
                self.pkg("install foo@1.0")
                self.pkg("set-authority -P test2")
                self.pkg("uninstall foo")
                # Change the image metadata back to where it was, in preparation
                # for the next test.
                self.pkg("set-authority -P test1")

        def test_zzz_uninstall_after_preferred_authority_removal(self):
                """Install a package from the preferred authority, remove the
                preferred authority, and attempt to remove the package."""
                self.pkg("install foo@1.0")
                self.pkg("set-authority -P test2")
                self.pkg("unset-authority test1")
                self.pkg("uninstall foo")


class TestImageCreateCorruptImage(testutils.SingleDepotTestCaseCorruptImage):
        """
        If a new essential directory is added to the format of an image it will
        be necessary to update this test suite. To update this test suite,
        decide in what ways it is necessary to corrupt the image (removing the
        new directory or file, or removing the some or all of contents of the
        new directory for example). Make the necessary changes in
        testutils.SingleDepotTestCaseCorruptImage to allow the needed
        corruptions, then add new tests to the suite below. Be sure to add
        tests for both Full and User images, and perhaps Partial images if
        situations are found where these behave differently than Full or User
        images.
        """

        # Only start/stop the depot once (instead of for every test)
        persistent_depot = True

        foo11 = """
            open foo@1.1,5.11-0
            add dir mode=0755 owner=root group=bin path=/lib
            add file /tmp/libc.so.1 mode=0555 owner=root group=bin path=/lib/libc.so.1
            close """

        misc_files = [ "/tmp/libc.so.1" ]

        PREFIX = "unset PKG_IMAGE; cd %s"
        
        def setUp(self):
                testutils.SingleDepotTestCaseCorruptImage.setUp(self)
                for p in self.misc_files:
                        f = open(p, "w")
                        # write the name of the file into the file, so that
                        # all files have differing contents
                        f.write(p)
                        f.close()
                        self.debug("wrote %s" % p)

        def tearDown(self):
                testutils.SingleDepotTestCaseCorruptImage.tearDown(self)
                for p in self.misc_files:
                        os.remove(p)

        def pkg(self, command, exit=0, comment=""):
                testutils.SingleDepotTestCaseCorruptImage.pkg(self, command, 
                    exit=exit, comment=comment, prefix=self.PREFIX % self.dir)
                        
        # For each test:
        # A good image is created at $basedir/image
        # A corrupted image is created at $basedir/image/bad (called bad_dir
        #     in subsequent notes) in verious ways
        # The $basedir/image/bad/final directory is created and PKG_IMAGE
        #     is set to that dirctory.

        # Tests simulating a corrupted Full Image

        def test_empty_var_pkg(self):
                """ Creates an empty bad_dir. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["catalog", "cfg_cache", "file", "pkg", "index"]),
                    ["var/pkg"])

                self.pkg("install foo@1.1")

        def test_var_pkg_missing_catalog(self):
                """ Creates bad_dir with only the catalog dir missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["catalog_absent"]), ["var/pkg"])

                self.pkg("install foo@1.1")

        def test_var_pkg_missing_cfg_cache(self):
                """ Creates bad_dir with only the cfg_cache file missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["cfg_cache_absent"]), ["var/pkg"])

                self.pkg("install foo@1.1")

        def test_var_pkg_missing_file(self):
                """ Creating bad_dir with only the file dir missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["file_absent"]), ["var/pkg"])

                self.pkg("install foo@1.1")

        def test_var_pkg_missing_pkg(self):
                """ Creates bad_dir with only the pkg dir missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl, set(["pkg_absent"]),
                    ["var/pkg"])

                self.pkg("install foo@1.1")

        def test_var_pkg_missing_index(self):
                """ Creates bad_dir with only the index dir missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl, set(["index_absent"]),
                    ["var/pkg"])

                self.pkg("install foo@1.1")

        def test_var_pkg_missing_catalog_empty(self):
                """ Creates bad_dir with all dirs and files present, but
                with an empty catalog dir.
                """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["catalog_empty"]), ["var/pkg"])

                # This is expected to fail because it will see an empty
                # catalog directory and not rebuild the files as needed
                self.pkg("install --no-refresh foo@1.1", exit=1)
                self.pkg("install foo@1.1")

        def test_var_pkg_missing_catalog_empty_hit_then_refreshed_then_hit(
            self):
                """ Creates bad_dir with all dirs and files present, but
                with an empty catalog dir. This is to ensure that refresh
                will work, and that an install after the refresh also works.
                """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["catalog_empty"]), ["var/pkg"])

                self.pkg("install --no-refresh foo@1.1", exit=1)
                self.pkg("refresh")
                self.pkg("install foo@1.1")


        def test_var_pkg_left_alone(self):
                """ Sanity check to ensure that the code for creating
                a bad_dir creates a good copy other than what's specified
                to be wrong. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl, set(), ["var/pkg"])

                self.pkg("install foo@1.1")

        # Tests simulating a corrupted User Image

        # These tests are duplicates of those above but instead of creating
        # a corrupt full image, they create a corrupt User image.

        def test_empty_ospkg(self):
                """ Creates a corrupted image at bad_dir by creating empty
                bad_dir.  """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["catalog", "cfg_cache", "file", "pkg", "index"]),
                    [".org.opensolaris,pkg"])

                self.pkg("install foo@1.1")

        def test_ospkg_missing_catalog(self):
                """ Creates a corrupted image at bad_dir by creating
                bad_dir with only the catalog dir missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["catalog_absent"]), [".org.opensolaris,pkg"])

                self.pkg("install foo@1.1")

        def test_ospkg_missing_cfg_cache(self):
                """ Creates a corrupted image at bad_dir by creating
                bad_dir with only the cfg_cache file missing.  """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["cfg_cache_absent"]), [".org.opensolaris,pkg"])

                self.pkg("install foo@1.1")

        def test_ospkg_missing_file(self):
                """ Creates a corrupted image at bad_dir by creating
                bad_dir with only the file dir missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl, set(["file_absent"]),
                    [".org.opensolaris,pkg"])

                self.pkg("install foo@1.1")

        def test_ospkg_missing_pkg(self):
                """ Creates a corrupted image at bad_dir by creating
                bad_dir with only the pkg dir missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl, set(["pkg_absent"]),
                    [".org.opensolaris,pkg"])

                self.pkg("install foo@1.1")

        def test_ospkg_missing_index(self):
                """ Creates a corrupted image at bad_dir by creating
                bad_dir with only the index dir missing. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl, set(["index_absent"]),
                    [".org.opensolaris,pkg"])

                self.pkg("install foo@1.1")

        def test_ospkg_missing_catalog_empty(self):
                """ Creates a corrupted image at bad_dir by creating
                bad_dir with all dirs and files present, but with an empty
                catalog dir. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["catalog_empty"]), [".org.opensolaris,pkg"])

                self.pkg("install --no-refresh foo@1.1", exit=1)

        def test_ospkg_missing_catalog_empty_hit_then_refreshed_then_hit(self):
                """ Creates bad_dir with all dirs and files present, but
                with an empty catalog dir. This is to ensure that refresh
                will work, and that an install after the refresh also works.
                """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["catalog_empty"]), [".org.opensolaris,pkg"])

                self.pkg("install --no-refresh foo@1.1", exit=1)
                self.pkg("refresh")
                self.pkg("install foo@1.1")

        def test_ospkg_left_alone(self):
                """ Sanity check to ensure that the code for creating
                a bad_dir creates a good copy other than what's specified
                to be wrong. """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl, set(),
                    [".org.opensolaris,pkg"])

                self.pkg("install foo@1.1")

# Tests for checking what happens when two images are installed side by side.

        def test_var_pkg_missing_cfg_cache_ospkg_also_missing_alongside(self):
                """ Each bad_dir is missing a cfg_cache
                These 3 tests do nothing currently because trying to install an
                image next to an existing image in not currently possible.  The
                test cases remain against the day that such an arrangement is
                possible.
                """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["cfg_cache_absent"]), [".org.opensolaris,pkg"])
                self.dir = self.corrupt_image_create(durl,
                    set(["cfg_cache_absent"]), ["var/pkg"], destroy=False)

                self.pkg("install foo@1.1")


        def test_var_pkg_ospkg_missing_cfg_cache_alongside(self):
                """ Complete Full image besides a User image missing cfg_cache
                """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl, set(), ["var/pkg"])
                self.dir = self.corrupt_image_create(durl,
                    set(["cfg_cache_absent"]), [".org.opensolaris,pkg"],
                    destroy=False)

                self.pkg("install foo@1.1")

        def test_var_pkg_missing_cfg_cache_ospkg_alongside(self):
                """ Complete User image besides a Full image missing cfg_cache
                """

                durl = self.dc.get_depot_url()
                self.pkgsend_bulk(durl, self.foo11)
                self.image_create(durl)

                self.dir = self.corrupt_image_create(durl,
                    set(["cfg_cache_absent"]), ["var/pkg"])
                self.dir = self.corrupt_image_create(durl, set(),
                    [".org.opensolaris,pkg"], destroy=False)

                self.pkg("install foo@1.1")


if __name__ == "__main__":
        unittest.main()
