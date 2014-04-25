#
# Makefile for the webinterface
#
# ----------------------------------------------------------------------
all: documentation

clean:
	(cd doc ; make clean)
	(cd wsgi ; rm -f *.pyc ; rm -f */*.pyc)
	(cd test ; rm -f *.pyc )

documentation:
	(cd doc ; make install)

gitcheck:
	git status

# FIXME: Now in medusa.git:
# /tmp/gitlocal/medusa/src/arclink/libs/python/seiscomp/arclink/manager.py
tools/manager.py:
	svn export svn+ssh://st32/srv/svn/repos/medusa/trunk/src/arclink/libs/python/seiscomp/arclink/manager.py tools/manager.py

# What's the right way to do a release
# with all the code we want, none we don't,
# and the manual?
#
DATESTR:=$(shell date +%Y.%j)
RELEASEFILE=webdc3-${DATESTR}.tgz
# Ideally, release-yyyy.jjj.tgz
#
release: clean gitcheck tools/manager.py
	make documentation
	rm -rf release
	mkdir release
	git archive -o release/archive.tar --prefix=webinterface/ HEAD
	(cd release; tar xpf archive.tar ; rm -f archive.tar )
	find release -path "*/.git/*" -delete
	find release -name webinterfaceEvent.py -delete  # NOT READY YET.
	cp -pr doc/webinterface.pdf doc/html release/webinterface/doc
	cp -p tools/manager.py release/webinterface/tools/manager.py
	@echo -n "Uncompressed size: "
	@du -sh release
	(cd release; tar cfz ../${RELEASEFILE} .  ) 
	rm -rf release
	@echo "Compressed: "
	@ls -l ${RELEASEFILE}
	@md5sum ${RELEASEFILE}
	@echo "Done. Final product is '${RELEASEFILE}'"

test:
	(cd test ; python testEvents.py )

demo:
	(cd test ; python manage.py )

