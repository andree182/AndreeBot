#!/bin/bash

if [ -d edits ]; then
	echo "Uploading edits..."
	find edits -type f | while read f; do
		realname=`echo $f | sed 's@edits/@@'`
		chromium-browser "https://en.wikivoyage.org/w/index.php?title=$realname&action=edit"
		kate "$f"
		while ps aux|grep -v grep|grep kate; do
			sleep 1
		done
		rm "$f"
	done

else
	mkdir edits

	while read p; do
		mkdir -p "`dirname \"edits/$p\"`"
		wget "https://en.wikivoyage.org/w/index.php?title=$p&action=raw" -O "edits/$p"
	done

	find edits -type f | while read f; do sed -i 's@{{[rR]ail-interchange/sandbox|@{{rint|@g' "$f"; done
fi
