#!/usr/bin/env python3

# Fixes pages in Category:Listing_with_Wikipedia_link_but_not_Wikidata_link
# For listings where wikipedia is specified, but no wikidata, wikidata is
# added.

import pywikibot
from pywikibot import pagegenerators as pg
import sys
import mwparserfromhell
import subprocess
import binascii
import os
import sys
import re

checkCommits = True
botName = "AndreeBot"

site = pywikibot.Site("en", "wikivoyage")

def transform(parsed):
	supported_headings = ["==Regions==", "==Cities==", "==Municipalities==", "==Other destinations=="]
	found = {}
	hdrs = parsed.filter_headings()
	match = "^ *\* *(\[\[(?P<ref>[^\]]*)\]\]||(?P<name>[^&—\-\.]*))( *(?P<sep>([—\-\.]|&mdash;)) *(?P<desc>.*)){0,1}$"

	for s in parsed.get_sections():
		if s.filter_headings() == []:
			continue
		if s.filter_headings()[0] not in supported_headings:
			continue
		found[str(s.filter_headings()[0])] = True
		
		res = []
		for l in str(s).split('\n'):
			if l.startswith('==') or l == '':
				res += l
				continue

			m = re.match(match, l)
			if m != None:
				print("* %s %s %s" % (
					"[[" + m.group("ref") + "]]" if m.group("ref") else m.group("name"),
					m.group("sep") if m.group("sep") else '',
					m.group("desc") if m.group("desc") else ''))
			else:
				print("    TODO", l)
		s.text = '\n'.join(res)

	#print(parsed)
	if not "==Regions==" in found and not "==Cities==" in found and not "==Municipalities==" in found:
		return ["!Missing Regions/Cities/Municipalities"]
	return True

def processPage(title):
	failures = []
	print("\nProcessing %s..." %(title))

	if os.path.exists(title):
		raw = open(title).read()
	else:
		page = pywikibot.Page(site, title)
		raw = raw
	parsed = mwparserfromhell.parse(raw)

	err = transform(parsed)
	if err != []:
		return err
	
	commit = True
	if checkCommits:
		# show diff, filter out most-likely-correct changes
		newText = str(parsed)
		open('f.1', 'w').write(raw)
		open('f.2', 'w').write(newText)
		subprocess.call("diff -pdau f.1 f.2 | grep -v '^[-+][-+][-+] f\.[12]'| grep '^[+-]' > f.diff", shell=True)
		diff = open('f.diff').read().split('\n')
		diff = list(filter(lambda l: l.strip() != '-}}', diff))
		diff = list(filter(lambda l: not l.startswith('+| wikidata=') and not l.startswith('+| wikidata ='), diff))
		diff = list(filter(lambda l: l!='', diff))

		if diff != []:
			subprocess.call("kdiff3 f.1 f.2", shell=True)
			commit = (input("Enter 'ok' to upload...") == 'ok')

	commit = False
	if commit:
		page.text = newText
		page.save("Convert cities/regions to templates", botflag = True)
	return failures

def processList(cat):
	timestamp = pywikibot.Page(site, "User_talk:" + botName).getVersionHistory()[0].timestamp
	counter = 0
	counterNum = 1

	if not os.path.exists("failed.regions"):
		open("failed.regions", "w")

	exceptions = {}
	
	for l in open("failed.regions", "r").read().split('\n'):
		i = l.split('|')
		if i == ['']:
			continue
		exceptions[i[0]] = i[1]
	exceptionsf = open("failed.regions", "a")
	
	cat = pywikibot.Category(site, cat)
	for a in cat.articles():
		if ':' in a.title():
			# skip the obvious internal stuff (templates, talk, user pages...)
			continue
		if a.title() in exceptions:
			continue
		fails = processPage(a.title())
		if fails != []:
			exceptionsf.write("%s|%s\n" % (a.title(), ', '.join(fails)))
			exceptionsf.flush()
		
		counter += 1
		if counter == counterNum:
			counter = 0
			if pywikibot.Page(site, "User_talk:" + botName).getVersionHistory()[0].timestamp > timestamp:
				print("Got kicked by someone!")
				break

if len(sys.argv) > 1:
	for p in sys.argv[1:]:
		processPage(p)
else:
	# processList("Outline_regions")
	processPage("Altiplano_(Bolivia)")
	# processPage("Metropolitan_Naples")
