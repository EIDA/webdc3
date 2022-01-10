#
# Makefile for the webinterface
#
# ----------------------------------------------------------------------
all: js/webdc3.min.js

.PHONY: all clean documentation gitcheck release test demo

# sudo {zypper|apt-get|yum} install npm
# npm install browserify babelify@8 babel-core babel-preset-env
# PATH=./node_modules/.bin:$PATH
js/webdc3.min.js: src/*
	mkdir -p js
	browserify --entry src/main.js --transform [ babelify --presets env --no-comments --minified ] --outfile $@

clean:
	(cd doc ; make clean)
	(cd wsgi ; rm -f *.pyc ; rm -f */*.pyc)
	(cd test ; rm -f *.pyc )

documentation:
	(cd doc ; make install)

gitcheck:
	git status


# What's the right way to do a release
# with all the code we want, none we don't,
# and the manual?
#
# Before doing a release, update the version number in 
#  - doc/templates/conf.py
#  - src/main.js
# and update doc/base/changelog.rst
# (e.g. find . -type f -exec grep --color 0\\.5 {} \; -print)
# Then 'make documentation' and check that it looks right.
# Finally, 'make gitcheck', and when clean, 'make release'

DATESTR:=$(shell date +%Y.%j)
RELEASEFILE=webdc3-${DATESTR}.tgz
# Ideally, release-yyyy.jjj.tgz
#
release: clean gitcheck
	make documentation
	rm -rf release
	mkdir release
	git archive -o release/archive.tar --prefix=webinterface/ HEAD
	(cd release; tar xpf archive.tar ; rm -f archive.tar )
	find release -path "*/.git/*" -delete
	find release -name webinterfaceEvent.py -delete  # NOT READY YET.
	cp -pr doc/webinterface.pdf doc/html release/webinterface/doc
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

