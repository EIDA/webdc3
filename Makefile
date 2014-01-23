#
# Makefile for the webinterface
#
# ----------------------------------------------------------------------

clean:
	(cd doc ; make clean)
	(cd wsgi ; rm -f *.pyc ; rm -f */*.pyc)
	(cd test ; rm -f *.pyc )

documentation:
	(cd doc ; make install)

svncheck:
	svn status

manager.py:
	svn export svn+ssh://st110/srv/svn/repos/medusa/trunk/src/arclink/libs/python/seiscomp/arclink/manager.py tools/manager.py

# What's the right way to do a release
# with all the code we want, none we don't,
# and the manual?
#
DATESTR:=$(shell date +%Y.%j)
RELEASEFILE=webdc3-${DATESTR}.tgz
# Ideally, release-yyyy.jjj.tgz
#
release: clean svncheck manager.py
	make documentation
	rm -rf release
	mkdir release
	(cd release; svn export svn+ssh://st110/srv/svn/repos/medusa/sandbox/webinterface )
	find release -path "*/.svn/*" -delete
	find release -type d -name .svn -delete
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

