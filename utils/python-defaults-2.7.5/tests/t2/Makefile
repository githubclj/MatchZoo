#!/usr/bin/make -f

include ../common.mk
DPY=$(DEBPYTHON_DEFAULT)
clean: clean-common

check:
	test -f debian/python-foo/usr/lib/python$(DPY)/dist-packages/foo.py
	test -f debian/python-foo/usr/lib/python$(DPY)/dist-packages/bar/bar.py
	grep -q pycompile debian/python-foo/DEBIAN/postinst
	grep -q pyclean debian/python-foo/DEBIAN/prerm
