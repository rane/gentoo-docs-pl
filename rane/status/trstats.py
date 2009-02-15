#!/usr/bin/python
__author__='Alin Dobre';
__copyright__='Copyright (c) 2005, Alin Dobre. Distributed under GPL-2 license';
__version__='0.2';

import sys, os, time

try:
  from xml import sax
except ImportError:
  sys.stderr.write('Could not import the SAX libs from the XML package'+os.linesep);
  sys.stderr.write('Please make sure that you have installed the pyxml package'+os.linesep);
  raise;
except:
  raise;

class CHandler(sax.handler.ContentHandler):
  def __init__(self):
    self.now=False;
    self.docs=[];

  def startElement(self, name, attrs):
    if name=='file':
      self.now=True;

  def endElement(self, name):
    self.now=False;

  def characters(self, chars):
    if self.now and ('handbook/2004.3/' not in chars) and ('handbook/2005.0/' not in chars):
      self.docs.append(chars.strip());

def parseDoc(name):
  parser=sax.sax2exts.make_parser();
  ch=CHandler();
  parser.setContentHandler(ch);
  inFile=file(name, 'r');
  parser.parse(inFile);
  inFile.close();
  return ch.docs;

def htmlHeader():
  print '''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<link rel="shortcut icon" href="http://www.gentoo.org/favicon.ico" type="image/x-icon">
<title>Gentoo official documentation translation status</title>
<link rel="stylesheet" href="styles.css" type="text/css">
</head>
<body>
<p class="topfont">Gentoo official documentation translations status<br/>(generated at: %s)</p>
''' % time.ctime(time.time());

def htmlFooter():
  print '''<br/><p style="text-align: center; width="100%">Generated using the
  <a href="http://dev.gentoo.org/~alin/scripts/trstats/trstats.py">trstats.py</a> script</p>'''
  print '</body></html>';

if os.environ.has_key('DOCSROOT'):
  htdocs=os.environ['DOCSROOT'];
else:
  sys.stderr.write('ERROR: The DOCSROOT variable was not defined in the environment'+os.linesep);
  sys.stderr.write('       Please set it to a valid directory and run this script again'+os.linesep);
  sys.exit(1);

if not os.path.isdir(htdocs):
  sys.stderr.write('ERROR: The directory indicated by the DOCSROOT variable is not a valid one'+os.linesep);
  sys.stderr.write('       Please set DOCSROOT to a valid directory and run this script again'+os.linesep);
  sys.exit(1);

langs=[];
generateHTML=False;
for p in sys.argv[1:]:
  if p=='--html':
    generateHTML=True;
  elif p=='--help':
    print sys.argv[0]+' [--html] [lang1] [lang2] ... [all]'
    print '\t--help will show this help'
    print '\t--html will generate html-formed output to stdout, otherwise text mode'
    print '\t"all" in the argument list, will display statistics for all languages'
    print '\tone or more languages in the argument list, will only display those languages'
    sys.exit();
  else:
    langs.append(p);

if len(langs)==0:
  langs=['all'];

rlangs=[];
if 'all' in langs:
  for obj in os.listdir(htdocs+'/doc'):
    if os.path.isfile(htdocs+'/doc/'+obj+'/metadoc.xml') and obj!='en':
      rlangs.append(obj);
else:
  for obj in langs:
    if os.path.isfile(htdocs+'/doc/'+obj+'/metadoc.xml') and obj!='en':
      rlangs.append(obj);

en_meta=parseDoc(htdocs+'/doc/en/metadoc.xml');

dirs={};
for lang in rlangs:
  tr_meta=parseDoc(htdocs+'/doc/'+lang+'/metadoc.xml');
  dirs[lang]={};
  for en_doc in en_meta:
    dir=en_doc[1:en_doc.find('/', 1)];
    if not dirs[lang].has_key(dir):
      dirs[lang][dir]=[0, 0];
    if en_doc.replace('/en/', '/'+lang+'/', 1) in tr_meta:
      dirs[lang][dir][1]+=1;
    dirs[lang][dir][0]+=1;

if generateHTML:
  htmlHeader();
  print '<table>';
  print '<th>lang</th>';
  for h in dirs[dirs.keys()[0]].keys():
    print '<th>/'+h+'</th>';
    print '<th>&nbsp;</th>';

for lang in dirs.keys():
  if generateHTML:
    print '<tr>';
    print '<td>'+lang+'</td>';
  for i in dirs[lang].keys():
    percent=dirs[lang][i][1]*100/dirs[lang][i][0];
    if generateHTML:
      print '<td>%d / %d (%d%%)</td>' % (dirs[lang][i][1], dirs[lang][i][0], percent);
      print '<td><img src="green.gif" width="%d" height="15"/><img src="red.gif" width="%d" height="15"/></td>' % (percent*1.2, (100-percent)*1.2);
    else:
      print '[%s]/%s:\tTotal: %d,\tTranslated: %d\t -> %d%%' % (lang, i, dirs[lang][i][0], dirs[lang][i][1], percent)
  print
  if generateHTML:
    print '</tr>';

if generateHTML:
  print '<table>';
  htmlFooter();

