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
fakeWID = False
botName = "AndreeBot"

site = pywikibot.Site("en", "wikivoyage")

def refToWDID(article):
	''' get wikidata for the ref '''

	article = str(article).strip()
	if article.startswith('[['):
		article = re.match("\[\[(?P<ref>[^\]]*)\]\].*", article).group("ref")

	if ('|' in article):
		article = article[:article.index('|')]

	if '#' in article:
		# avoid subsections, it's not the right wikidata ID
		return ''

	page = pywikibot.Page(site, article)
	if page.isRedirectPage():
		print("!!!!!!!!!!!!!!!!!!!!! REDIRECT: %s" % article)
		page = page.getRedirectTarget()
	if page.pageid != 0:
		return pywikibot.ItemPage.fromPage(page).getID()
	return ''

def addMarkerWikidata(parsed):
	# if there are city markers already, just without wikidata...
	for template in parsed.filter_templates():
		if (template.name.strip().lower() == "marker" or template.name.strip().lower() == "listing") and \
			template.has_param("type") and \
			(template.get("type").value.lower().strip() == "city" or template.get("type").value.lower().strip() == "vicinity") and \
			(not template.has_param("wikidata") or template.get("wikidata").value.strip() == ''):
				wdid = refToWDID(template.get("name").value)
				if wdid != '':
					template.add('wikidata', wdid)

def addRegionShapes(parsed):
	''' if there's regionlist, but no geoshapes yet... '''
	if not [t for t in parsed.filter_templates() if t.name.lower().strip() == "regionlist"] or \
		[t for t in parsed.filter_templates() if t.name.lower().strip() == "mapshape" and t.has("type") and t.get("type").value == "geoshape"]:
			return

	newRegionshapes = []
	for t in parsed.filter_templates():
		if not t.name.lower().strip() == "regionlist":
			continue

		for i in range(1, 100): # :-)
			if t.has("region%dname" % i):
				wdID = refToWDID(t.get('region%dname' % i).value)
				newRegionshapes += ["{{mapshape|type=geoshape|fill=%s|title=%s|wikidata=%s}}\n" %
					(t.get('region%dcolor' % i).value.strip(), t.get('region%dname' % i).value.strip(), wdID)]

	if newRegionshapes:
		for s in parsed.get_sections(levels=[2], include_lead = True):
			if s.filter_headings() != [] and \
				(s.filter_headings()[0] == "==Regions==" or s.filter_headings()[0] == "==Provinces=="):
				s.append(''.join(newRegionshapes))
				break

def transform(parsed):
	supported_headings = ["==Regions==", "==Provinces==", "==Cities==", "==Municipalities==", "==Other destinations=="]
	found = {}
	hdrs = parsed.filter_headings()
	match = "^(?P<prefix>( *:*\* *))(\[\[(?P<ref>[^\]]*)\]\]|(?P<name>[^&—\-\.]*))((?P<sep>( *([—\-\.]|&mdash;|) *))(?P<desc>.*)){0,1}$"
	rv = True

	nomap = not '{{mapframe' in str(parsed).lower()
	tr = []
	for s in parsed.get_sections(levels=[2], include_lead = True):
		if s.filter_headings() == [] or \
		   s.filter_headings()[0] not in supported_headings:
			tr += [s]
			continue
		found[str(s.filter_headings()[0])] = True
		
		res = []
		for l in str(s).split('\n'):
			if l.startswith('==') or l == '':
				res += [l]

				if l.startswith('==') and 'Cities' in l:
					markerType = '|type=city'
					if nomap:
						res += ["{{mapframe}}"]
				elif l.startswith('=='):
					markerType = ''
				
				continue

			m = re.match(match, l)
			if m != None and m.group("ref"):
				if "[[" in m.group("desc"):
					print("MULTI-LINK?:", l)
				title = "[[" + m.group("ref") + "]]" if m.group("ref") else m.group("name")
				
				if fakeWID:
					wdID = 'Q1234'
				else:
					wdID = ''
				if m.group("ref") and wdID == '':
					wdID = refToWDID(m.group("ref"))
				
				res += ['%s{{marker%s|name=%s|wikidata=%s}}%s%s' % (
					m.group("prefix"),
					markerType, title, wdID,
					m.group("sep") if m.group("sep") else ('' if not m.group("desc") else " "),
					m.group("desc") if m.group("desc") else '')]
			elif m != None and m.group("name"):
				print("NO LINK    :", l)
				res += [l]
			elif re.match('\[\[(Image|File):.*\]\]', l) or l.startswith('| ') or l.startswith('}}') or l.startswith("<!--"):
				print("COPY    :", l)
				res += [l]
			else:
				print("    ERROR (!regex.match) -> skiping section: ", l)
				res = str(s).split('\n')
				break

		tr += ['\n'.join(res)]

	if not "==Regions==" in found and not "==Cities==" in found and not "==Municipalities==" in found:
		return False, ["!Missing Regions/Cities/Municipalities"]
	return rv, ''.join([str(x) for x in tr])

def transformRegions(parsed):
	tr = []
	rv = True
	for s in parsed.get_sections(levels=[2], include_lead = True):
		if (s.filter_headings() == []) or \
		   (s.filter_headings()[0] not in ["==Regions=="]) or \
		   ("{{regionlist" in str(s).lower()):
			tr += [s]
			continue 

		hasRegionEntry = False
		tr += ["==Regions==\n"]
		tr2 = []
		idx = 1
		for l in str(s).split('\n'):
			if l == '':
				continue
			if l.startswith('=='):
				continue
			if not re.match("^\* *\{\{marker.*", l):
				print("COPY    :", l)
				tr += [l + "\n"]
				continue
			t = mwparserfromhell.parse(l).filter_templates()[0]

			if not hasRegionEntry:
				tr += ["{{Regionlist\n"]
				hasRegionEntry = True

			tr += ["|region%dname = %s\n|region%dcolor={{StdColor|t%d}}\n|region%ditems=\n|region%ddescription=\n\n" %
					(idx, t.get('name').value, idx, idx, idx, idx)]
			tr2 += ["{{mapshape|type=geoshape|fill={{StdColor|t%d}}|title=%s|wikidata=%s}}\n" %
					(idx, t.get('name').value, t.get('wikidata').value)]
			idx += 1
		if hasRegionEntry:
			tr += ["}}\n"]
		tr += tr2

	return rv, ''.join([str(x) for x in tr])

def processPage(title):
	failures = []
	print("\nProcessing %s..." %(title))

	if os.path.exists(title):
		raw = open(title).read()
	else:
		page = pywikibot.Page(site, title)
		raw = page.text
	parsed = mwparserfromhell.parse(raw)
	addMarkerWikidata(parsed)

	err, newText = transform(parsed)
	if err != True:
		print('%s errors:\n\n%s' % (title, newText))
		return err

	parsed = mwparserfromhell.parse(newText)
	addRegionShapes(parsed)
	err, newText = transformRegions(parsed)
	if err != True:
		print('%s errors:\n\n%s' % (title, newText))
		return err
	
	commit = True
	if checkCommits:
		# show diff, filter out most-likely-correct changes
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

	#commit = False
	if commit:
		page.text = newText
		page.save("transform city-like links to markers", botflag = True)
	else:
		open(title + ".new", 'w').write(newText)
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
	processList("Region_markers_without_wikidata")

