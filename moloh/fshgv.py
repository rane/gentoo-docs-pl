#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2005 Lukasz Strzygowski <lucass@gentoo.org> 
# Distributed under the terms of the GNU General Public License v2
#
#
# Current release: 1.2
#
# Changelog:
#  * 1.2
#   - new text-wrapping function
#   - added handling of <table>s
#
#  * 1.1
#   - fixed handling of <uri>s without "link" attribute
#
#  * 1.0
#   - fixed text wrapping in <author>s
#   - fixed handling of <author>s without <mail>s inside
#
# Known bugs:
#  * some lines have length maxwidth + 1
#
# PyLint settings:
#  * i don't need __revision__
#    pylint: disable-msg=W0103
#
#  * setdefaultencoding _is_ in sys
#    pylint: disable-msg=E0611
#
#


"""
GuideXML to text converter
"""

import locale
import math
import os
import re
import sys
import tempfile

from elementtree import ElementTree


class Parser(object):
    """Parser of GuideXML."""


    def make_title(self, title, underline = None):
        """Wrap title to specified length and add optional underline."""

        title = title.strip()
        wrapped = self.textwrap(title, self.width)
        text = "\n".join(wrapped)

        if underline:
            maxlen = max(len(line) for line in wrapped)
            uline = underline * maxlen
            text = text + "\n" + uline

        return text


    def default_handler(self, node):
        """Default handler."""

        text = "".join(child[1] for child in self.iter_children(node))

        return text


    def handle_author(self, node):
        """Transform 'author' tags into:

        name <email> - title
        """

        title = node.attrib["title"]

        # has link inside
        if len(node) == 1:
            name = node[0].text
            mail = node[0].attrib["link"]
            text = "%s <%s> - %s" % (name, mail, title)
        else:
            name = node.text
            text = "%s - %s" % (name, title)

        wrapped = self.textwrap(text, self.width)
        text = "\n".join(wrapped)

        return text


    def handle_guide(self, node):
        """Transform 'guide' tags into:

        title
        =====

        <chapters>

        <authors>
        """

        title = ""
        chapters = []
        authors = []

        for tag, value in self.iter_children(node):
            if tag == "abstract":
                title = value
            elif tag == "chapter":
                chapters.append(value)
            elif tag == "author":
                authors.append(value)

        title = self.make_title(title, "=")
        chapters = "\n".join(chapters)
        authors = "\n".join(authors)


        text = "%s\n\n%s\n\nAutorzy:\n%s" % (title, chapters, authors)

        return text


    def handle_chapter(self, node):
        """Transform 'chapter' tags into:

        title
        -----

        <sections>
        """


        title = ""
        sections = []

        for tag, value in self.iter_children(node):
            if tag == "title":
                title = value
            elif tag == "section":
                sections.append(value)

        self.chapter_count += 1

        title = "%d. %s" % (self.chapter_count, title)
        title = self.make_title(title, "-")
        sections = "\n".join(sections).lstrip()

        text = "\n%s\n\n%s" % (title, sections)


        return text


    def handle_pre(self, node):
        """Transform 'pre' tags into:

        .-----------.
        | <caption> |
        |-------------.
        | <some text> |
        `-------------'
        """

        caption = node.attrib["caption"]
        text = self.default_handler(node)

        row1 = ".%s." % ("-" * (len(caption) + 2))
        row2 = "| %s |" % caption

        lines = text.split("\n")[1:]
        lines = ["| %s" % line for line in lines]

        maxlen = max(len(line) for line in lines)
        if len(caption) > maxlen:
            maxlen = len(caption) + 2

        row3 = "|%s." % ("-" * maxlen)
        row4 = "`%s'" % ("-" * maxlen)

        lines = ["%s%s |" % (line, " " * (maxlen-len(line))) for line in lines]
        text = "\n".join(lines)

        text = "%s\n%s\n%s\n%s\n%s" % (row1, row2, row3, text, row4)

        return text



    def handle_table(self, node):
        """Transform 'table' tags into:

        .-----------------------------.
        | hdr1 | hdr2          | hdr3 |
        |-----------------------------|
        | foo  | bar           | oni  |
        | blah | blaaaaaaaaaah | blah |
        `-----------------------------'
        """

        rawrows = [[self.default_handler(field) for field in row] for row in node]
        rawcols = zip(*rawrows)

        maxwidths = [max([len(str(item)) for item in col]) for col in rawcols]
        colcount = len(maxwidths)
        colsep = " | "
        prefix = "| "
        postfix = " |"

        decowidth = len(prefix + postfix) + len(colsep) * (colcount - 1)
        while (sum(maxwidths) > (self.width - decowidth)):
            m = max(maxwidths)
            maxwidths[maxwidths.index(m)] -= 1
        maxwidth = sum(maxwidths)

        rows = []
        for row in rawrows:
            myrows = map(lambda (i, x): self.textwrap(x, maxwidths[i]), enumerate(row))
            myrows = map(None, *myrows)
            myrows = [[x or '' for x in item] for item in myrows]
            rows.append(myrows)

        columns = map(None, *reduce(lambda a,b:a+b, rows))
        maxwidth = sum(maxwidths)
        mywidth = (maxwidth + len(colsep) * (colcount - 1) + len(prefix + postfix) - 2)
        rowsep = "|" + "-" * mywidth + "|"
        firstrow = "." + "-" * mywidth + "."
        lastrow = "`" + "-" * mywidth + "'"

        myrows = []
        for logirows in rows:
            myrows.append(rowsep)
            for row in logirows:
                fields = (field.ljust(width) for (field, width) in zip(row, maxwidths))
                myrows.append(prefix + colsep.join(fields) + postfix)
        myrows = myrows[1:]

        result = "%s\n%s\n%s" % (firstrow, "\n".join(myrows), lastrow)

        return result


    def handle_section(self, node):
        """Transform 'section' tags into:

        title
        ^^^^^

        <body>

        <links>
        """

        title = ""
        body = ""
        links = []
        self.links = []


        for tag, value in self.iter_children(node):
            if tag == "title":
                title = value
            elif tag == "body":
                body = value

        for i, link in enumerate(self.links):
            number = i + self.link_count + 1
            prefix = " %d. " % number
            indent = len(prefix)
            wrapped = self.textwrap(link, self.width - indent)
            mylink = prefix + ("\n%s" % (" " * indent)).join(wrapped)
            links.append(mylink)

        self.link_count += len(self.links)

        text = body

        if title:
            title = self.make_title(title, "^")
            text = "\n%s\n\n%s" % (title, text)

        if links:
            links = "\n".join(links)
            text = "%s\n\n%s" % (text, links)

        return text


    def handle_body(self, node):
        """Transform 'body' tags into wrapped text."""


        text = ""

        notwrapped = ("pre", "table", "ul", "ol")

        for tag, value in self.iter_children(node):
            if not value.strip():
                continue

            if tag in notwrapped:
                text = "%s\n\n%s" % (text, value)
            else:
                wrapped = self.textwrap(value, self.width)
                text = "%s\n\n%s" % (text, "\n".join(wrapped))

        text = text[2:]

        return text


    def handle_warn(self, node):
        """Transform 'warn' tags into:

        Ostrzeżenie: <text>
        """

        text = "Ostrzeżenie: %s" % self.default_handler(node)

        return text


    def handle_note(self, node):
        """Transform 'note' tags into:

        Uwaga: <text>
        """

        text = "Uwaga: %s" % self.default_handler(node)

        return text


    def handle_comment(self, node):
        """Transform 'comment' tags into:

        (<text>)
        """

        text = "(%s)" % self.default_handler(node)

        return text


    def handle_mail(self, node):
        """Transform 'mail' tags into:

        <text>[<number>]

        Link will be inserted in a list after current section.
        """

        if "link" in node.attrib:
            link = node.attrib["link"]
            if not link in self.links:
                self.links.append(link)
            number = self.link_count + self.links.index(link) + 1
            text = "%s[%d]" % (node.text, number)
        else:
            text = node.text

        return text


    def handle_figure(self, node):
        """Transform 'figure' tags into:

        Ilustracja[<number>]: <caption>

        Link will be inserted in a list after current section.
        """

        link = node.attrib["link"]
        if link[0] == "/":
            link = "http://gentoo.org%s" % link
        self.links.append(link)

        number = self.link_count + len(self.links)
        caption = node.attrib["caption"]

        text = "Ilustracja[%d]: %s" % (number, caption)

        return text


    def handle_ul(self, node):
        """Transform 'ul' tags into:

         * <li>
         * <li>
        """

        items = []

        for tag, value in self.iter_children(node):
            if tag != "li":
                continue
            wrapped = self.textwrap(value.strip(), self.width-3)
            item = "\n   ".join(wrapped)
            items.append(item)

        text = " * %s" % "\n * ".join(items)

        return text


    def handle_ol(self, node):
        """Transform 'ol' tags into:

         1. <li>
         2. <li>
        """

        text = ""
        i = 0
        for tag, value in self.iter_children(node):
            if tag != "li":
                continue
            i = i + 1
            prefix = " %d. " % i
            wrapped = self.textwrap(value.strip(), self.width - len(prefix))
            item = ("\n%s" % (" "*len(prefix))).join(wrapped)
            text += "\n%s%s" % (prefix, item)

        return text


    def handle_p(self, node):
        """Transform 'p' tags with default handler and strip them."""

        text = self.default_handler(node).strip()

        return text


    def handle_uri(self, node):
        """Transform 'uri' tags into:

        <text>[<number>]

        Link will be inserted in a list after current section.
        """


        if not "link" in node.attrib:
            return node.text


        link = node.attrib["link"]

        if link[0] == "/":
            link = "http://gentoo.org%s" % link


        # if link refers to the same document, we just ignore it
        if link[0] != "#":
            if not link in self.links:
                self.links.append(link)
            number = self.link_count + self.links.index(link) + 1
            text = "%s[%d]" % (node.text, number)

        else:
            text = node.text

        return text

    
    def iter_children(self, node):
        """Iterate over node's children and run appropriate handlers."""

        handlers = { \
            "author": self.handle_author,
            "body": self.handle_body,
            "chapter": self.handle_chapter,
            "comment": self.handle_comment,
            "figure": self.handle_figure,
            "guide": self.handle_guide,
            "mail": self.handle_mail,
            "note": self.handle_note,
            "ol": self.handle_ol,
            "p": self.handle_p,
            "pre": self.handle_pre,
            "section": self.handle_section,
            "table": self.handle_table,
            "ul": self.handle_ul,
            "uri": self.handle_uri,
            "warn": self.handle_warn,
        }

        skipped = ("date", "subtitle", "summary", "version")

        if node.text:
            yield "TEXT", node.text

        for child in node:
            tag = child.tag

            if tag in handlers:
                retval = handlers[tag](child)

            elif tag in skipped:
                retval = ""

            else:
                retval = self.default_handler(child)

            yield tag, retval

            if child.tail:
                yield "TEXT", child.tail


    def parse(self, path):
        """Parse specified document and return it's textual representation."""

        tree = ElementTree.parse(path)
        root = tree.getroot()
        text = self.handle_guide(root)

        return text


    def textwrap(self, text, width):
        """Wrap text to specified width."""

        # FIXME: refactor this

        text = re.sub(
            r'\S{'+str(width)+r',}',
            lambda m: '\n'.join(
                m.group()[width * i : width * (i+1)] for i in \
                xrange(int(math.ceil(len(m.group())/float(width))))),
            text \
        )

        result = reduce( \
            lambda line, word, width = width: '%s%s%s' % (
                line,
                len(line[line.rfind('\n')+1:]) + len(word.split('\n', 1)[0]) >= width \
                    and "\n" \
                    or " ",
                word
            ),
            text.split(' ')
        )

        result = result.split("\n")

        return result


    def __init__(self, width):
        """Initialize."""

        self.chapter_count = 0
        self.link_count = 0
        self.links = []
        self.width = width



def _preprocess(srcpath, dstpath):
    """Remove from document unnecessary whitespaces and
    save under other name in order to make parsing easier.
    """

    text = file(srcpath).read()
    pre = re.compile("<pre *(.*?)</pre>", re.DOTALL)

    all_pres = pre.findall(text)

    for i, pre in enumerate(all_pres):
        text = text.replace(pre, "\a%d\a" % i)

    text = re.sub("\n\s*</", "</", text)
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")
    while "  " in text:
        text = text.replace("  ", " ")

    for i, pre in enumerate(all_pres):
        text = re.sub("\a%d\a" % i, pre.strip(), text)

    file(dstpath, "w").write(text)


def run(argv = sys.argv):
    """Run fshgv."""

    if len(argv) < 2:
        sys.exit("Usage: %s [newsletter.xml] <max width>" % __file__)

    reload(sys)
    sys.setdefaultencoding("utf-8")

    srcpath = argv[1]

    if len(argv) > 2:
        width = int(argv[2])
    else:
        width = 80


    tmpfd, tmppath = tempfile.mkstemp(suffix = "fshgv", text = True)
    os.close(tmpfd)

    _preprocess(srcpath, tmppath)

    parser = Parser(width)

    textual = parser.parse(tmppath)
    os.unlink(tmppath)    

    textual = textual.encode(locale.getpreferredencoding(), "ignore")

    print textual


if __name__ == "__main__":
    run()
