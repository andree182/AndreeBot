#!/usr/bin/env python3

# Fixes pages in Category:Listing_with_Wikipedia_link_but_not_Wikidata_link
# For listings where wikipedia is specified, but no wikidata, wikidata is
# added.

import pywikibot
from pywikibot import pagegenerators as pg
import sys
import mwparserfromhell
import subprocess

valid_templates = ["listing", "see", "do", "go", "eat", "buy", "sleep", "drink"]

site = pywikibot.Site("en", "wikivoyage")
#repo = site.data_repository()

wsite = pywikibot.Site("en", "wikipedia")

def processPage(title):
	print("Processing %s..." %(title))

	page = pywikibot.Page(site, title)
	parsed = mwparserfromhell.parse(page.text)

	for template in parsed.filter_templates():
		if template.name.strip() in valid_templates:
			paramNames = [param.name.lower().strip() for param in template.params]
			if 'wikipedia' in paramNames and not 'wikidata' in paramNames:
				# fill it in
				wIdx = paramNames.index('wikipedia')
				wikipedia = template.params[wIdx].value
				wpage = pywikibot.Page(wsite, wikipedia)
				witem = pywikibot.ItemPage.fromPage(wpage)
				wID = witem.getID()
				template.add("wikidata", wID)

	newText = str(parsed)
	open('f.1', 'w').write(page.text)
	open('f.2', 'w').write(newText)
	subprocess.call("diff -pdau f.1 f.2 | grep '^[+-]'", shell=True)

	input("Do Ctrl+C or enter to upload...")

	page.text = newText
	page.save("Add wikidata ID(s) derived from wikipedia parameter(s)")

def processList(page):
	cat = pywikibot.Category(site, 'Listing_with_Wikipedia_link_but_not_Wikidata_link')
	for a in cat.articles():
		if ':' in a.title():
			# skip the obvious internal stuff (templates, talk, user pages...)
			continue
		processPage(a.title())

processList("Category:Listing_with_Wikipedia_link_but_not_Wikidata_link")
