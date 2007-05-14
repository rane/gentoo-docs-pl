#!/usr/bin/env python
# Copyright 2005 Lukasz Strzygowski <lucass@gentoo.org> 
# Distributed under the terms of the GNU General Public License v2

import os
import re
import sys
import time
import getopt
import urllib2

class DocGet(object):
	"""Main class of DocGet."""
	
	_metadoc_path = "~/.docget"
	_metadoc_timeout = 600
	
	def _get_metadoc_iter(self, url, refetch):
		"""Return iterator of metadoc content.

		url - url of metadoc.xml
		referch - force redownloading metadoc (by default it's cached for ten minutes)
		"""	
		
		mdpath = os.path.expanduser(self._metadoc_path)
		reget = False

		if not os.path.exists(mdpath) or refetch:
			reget = True
		else:
			mtime = os.stat(mdpath)[-1]
			curtime = time.time()
			if (curtime - mtime) > self._metadoc_timeout:
				reget = True

		if reget:
			mdoc = urllib2.urlopen(url)
			fp = file(mdpath, "w")
			fp.write(mdoc.read())
			fp.close()

		return file(mdpath).xreadlines()
		
	
	def _get_documents_iter(self, metadoc):
		"""Return iterator of all documents in metadoc.

		metadoc - list of iterator of metadoc content
		"""
		
		fidres = re.compile(r'^.*<file id="[^"]*">(.*)</file>.*$')

		for line in metadoc:
			m = fidres.match(line)
			if not m: continue
			yield m.group(1)
		
	
	def _get_matched_documents(self, pattern, documents):
		"""Look in a list of documents for those matching specified pattern.

		pattern - regular expression
		documents - list or iterator of document names
		"""
		
		docres = re.compile(pattern)
		matches = [doc for doc in documents if docres.search(doc)]
	
		return matches
		

	def _get_options(self, argv):
		"""Parse command line options.

		argv - usually sys.argv, first item is ommited as a program's name
		"""
		
		usage = "Usage: %s <arguments> [document]\n\n" \
			 "[document] can be a regular expression.\n\n" \
			 "Available arguments:\n" \
			 "	-f		Overwrite file if already exists\n" \
			 "	-l <lang>	Use specified language\n" \
			 "	-r		Refetch index of documents even if it's newer than 10 minutes\n" \
			 "	-u <url>	Use index of documents other than default" % __file__

		options = {"force": False, "lang": "en", "refetch": False, "pattern": [],
			"url": "http://www.gentoo.org/doc/en/metadoc.xml?passthru=1"}
		
		try: opts, args = getopt.getopt(argv[1:], "fhl:ru")
		except:	sys.exit(usage)

		if len(args) != 1: sys.exit(usage)

	
		for opt, arg in opts:
			if opt == "-f": options["force"] = True
			elif opt == "-l": options["lang"] = arg
			elif opt == "-r": options["refetch"] = True
			elif opt == "-u": options["url"] = arg

			elif opt == "-h":
				print usage
				sys.exit()

		options["pattern"] = args[0]
		
		return options
	
	
	def run(self, argv = sys.argv):
		"""Run DocGet.

		argv - list of command line options, first item is treated as a program's name
		"""
		
		opts = self._get_options(argv)
		pattern = opts["pattern"]
		lang = opts["lang"]
		metadoc = self._get_metadoc_iter(opts["url"], opts["refetch"])
				
		documents = self._get_documents_iter(metadoc)
		matches = self._get_matched_documents(pattern, documents)

		if len(matches) > 1:
			sys.stderr.write("I found more than one document matching your search:\n")
			sys.stderr.write("\n".join(["\t%s" % doc for doc in matches]))
			sys.stderr.write("\nYou need to be more precise.\n")
			sys.exit(1)

		if not matches:
			sys.stderr.write("Sorry, I didn't find any document matching your pattern.\n")
			sys.exit(1)

		url = "http://www.gentoo.org/%s?passthru=1" % (matches[0].replace("/en/", "/%s/" % lang))
		
		print "Downloading %s..." % url
		
		try:
			u = urllib2.urlopen(url)
		except urllib2.HTTPError, e:
			sys.stderr.write("I couldn't download specified document. Please make sure it is\n")
			sys.stderr.write("already available in specified language. Here is an error message:\n")
			sys.stderr.write("\tHTTP Error %d: %s\n" % (e.code, e.msg))
			sys.exit(1)

		filename = re.search(r'/([^/\?]*)\?', u.url).group(1)
	
		if os.path.exists(filename) and not opts["force"]:
			print "%s already exists in current directory. If you" % filename
			print "want it to be overwritten, run docget with -f." 
			sys.exit(1)

		fp = file(filename, "w")
		fp.write(u.read())

		sys.exit(0)
		

if __name__ == "__main__":
	docget = DocGet()
	docget.run(sys.argv)
