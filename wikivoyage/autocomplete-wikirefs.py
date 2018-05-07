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

checkCommits = True
botName = "AndreeBot"

validTemplates = ["listing", "see", "do", "go", "eat", "buy", "sleep", "drink"]

site = pywikibot.Site("en", "wikivoyage")
#repo = site.data_repository()

wsite = pywikibot.Site("en", "wikipedia")

def processPage(title):
	failures = []
	print("\nProcessing %s..." %(title))

	page = pywikibot.Page(site, title)
	if not page.exists():
		# Esp. if called from command line...
		print("Nonexistent page!")
		return ["Nonexistent page"]
	parsed = mwparserfromhell.parse(page.text)

	for template in parsed.filter_templates():
		if template.name.lower().strip() in validTemplates:
			paramNames = [param.name.lower().strip() for param in template.params]
			if 'wikipedia' in paramNames and (not 'wikidata' in paramNames or template.params[paramNames.index('wikidata')].value.strip() == ''):
				# fill it in
				wIdx = paramNames.index('wikipedia')
				wikipedia = template.params[wIdx].value.strip()
				# print(wikipedia)
				if wikipedia == "":
					failures += [wikipedia]
					continue
				if '#' in wikipedia:
					failures += [wikipedia]
					# Wikidata to part of wikipedia article doesn't exist...
					continue

				wpage = pywikibot.Page(wsite, wikipedia)
				if wpage.isRedirectPage():
					wpage = wpage.getRedirectTarget()
				if wpage.pageid == 0:
					print("!!! non-existent wikipedia article '%s'" % (wikipedia))
					failures += [wikipedia]
					continue

				witem = pywikibot.ItemPage.fromPage(wpage)
				wID = witem.getID()
				# TODO: "Wikipedia" param name breaks this
				template.add("wikidata", wID, before="wikipedia")

	commit = True
	newText = str(parsed)
	if checkCommits:
		# show diff, filter out most-likely-correct changes
		open('f.1', 'w').write(page.text)
		open('f.2', 'w').write(newText)
		subprocess.call("diff -pdau f.1 f.2 | grep -v '^[-+][-+][-+] f\.[12]'| grep '^[+-]' > f.diff", shell=True)
		diff = open('f.diff').read().split('\n')
		diff = list(filter(lambda l: l.strip() != '-}}', diff))
		diff = list(filter(lambda l: not l.startswith('-| wikipedia=') and not l.startswith('-| wikipedia ='), diff))
		diff = list(filter(lambda l: not l.startswith('+| wikidata=') and not l.startswith('+| wikidata ='), diff))
		diff = list(filter(lambda l: l!='', diff))

		if diff != []:
			subprocess.call("kdiff3 f.1 f.2", shell=True)
			commit = (input("Enter 'ok' to upload...") == 'ok')

	if commit:
		page.text = newText
		page.save("Add wikidata ID(s) derived from wikipedia parameter(s)", botflag = True)
	return failures

def processList(cat, first):
	timestamp = pywikibot.Page(site, "User_talk:" + botName).getVersionHistory()[0].timestamp
	counter = 0
	counterNum = 1

	if not os.path.exists("failed.autocomplete"):
		open("failed.autocomplete", "w")

	exceptions = {}
	
	for l in open("failed.autocomplete", "r").read().split('\n'):
		i = l.split('|')
		if i == ['']:
			continue
		exceptions[i[0]] = i[1]
	exceptionsf = open("failed.autocomplete", "a")
	
	cat = pywikibot.Category(site, cat)
	for a in cat.articles():
		if ':' in a.title():
			# skip the obvious internal stuff (templates, talk, user pages...)
			continue
		if a.title() in exceptions:
			continue
		if a.title() < first:
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

if len(sys.argv) > 1 and sys.argv[1] == '--first':
	first = sys.argv[2]
	sys.argv = sys.argv[2:]
else:
	first = ''

if len(sys.argv) > 1:
	for p in sys.argv[1:]:
		processPage(p)
else:
	processList("Listing_with_Wikipedia_link_but_not_Wikidata_link", first)
