#!/bin/sh

if [ ! -f whatlinks.tmp ]; then
	wget "https://en.wikivoyage.org/wiki/Special:WhatLinksHere/Template:Rail-interchange/sandbox" -O whatlinks.tmp
fi

grep '^<li><a href="/wiki' whatlinks.tmp > whatlinks.tmp2
sed whatlinks.tmp2 -e 's@^.*/wiki/@@' -e 's@.*title="@@' -e 's@">.*@@' |grep -v ":" > whatlinks.list
