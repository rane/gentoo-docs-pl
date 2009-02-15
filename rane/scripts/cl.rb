#!/usr/bin/ruby
# Check docs for links to .../en/... for docs that exist in $LANG
# Usage: run cl.rb from .../doc/$LANG
require 'rexml/document'
require 'find'
d=`pwd`.strip.split('/')[-1]
raise 'Having a bit of fun?' if d == 'en'
Find.find('.'){|f|
 if f =~ /\.xml$/ then
  x=REXML::Document.new(File.new(f))
  xp = x.root.name=='metadoc' ? '/metadoc/files/file' : '//uri'
  REXML::XPath.each(x, xp){|el|
    link=el.attributes['link'] ? el.attributes['link'] : el.text
    if link =~ /\/en\// then
      cf = "../.." + link.sub("http://www.gentoo.org/","/")
      cf << "/index.xml" if File.directory?(cf)
      puts "#{f}::#{link}" if File.file?(cf.sub(/\/en\//,"/#{d}/"))
    end
  }
 end
}
