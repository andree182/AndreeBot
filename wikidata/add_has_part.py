#!/usr/bin/env python3

# Searches for wikidata entries without "has parts" claims and adds them acc.
# to the reverse claim ("is part of") in the child items.

# Currently used for metros only, but it could be extended to keep "has parts"
# and "is part of" in sync.

import pywikibot
from pywikibot import pagegenerators as pg
import sys

site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()

queryEmptyMetros = open("metros-without-has-parts.sparql").read()
queryMetroParts = open("metro-parts.sparql").read()

if len(sys.argv) > 1:
	generatorEmptyMetros = [pywikibot.ItemPage(repo, sys.argv[1])]
else:
	generatorEmptyMetros = pg.WikidataSPARQLPageGenerator(queryEmptyMetros, site=site)

for item in generatorEmptyMetros:
	metroID = item.getID()
	print("Processing %s" % (metroID))

	item.get()
	if 'P527' in item.claims:
		print("    Skippping, there are P527 claims already: ", metroID)
		continue
	claim = pywikibot.Claim(repo, "P527")

	generatorMetroParts = pg.WikidataSPARQLPageGenerator(queryMetroParts % metroID, site=site)
	for part in generatorMetroParts:
		print("...Adding %s" % (part.getID()))
		claim.setTarget(part)
		item.addClaim(claim)
