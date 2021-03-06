# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         sfp_whois
# Purpose:      SpiderFoot plug-in for searching Whois servers for domain names
#               and netblocks identified.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2015
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
# -------------------------------------------------------------------------------

import pythonwhois
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent


class sfp_whois(SpiderFootPlugin):
    """Whois:Footprint,Investigate,Passive:Public Registries::Perform a WHOIS look-up on domain names and owned netblocks."""

    # Default options
    opts = {
    }

    # Option descriptions
    optdescs = {
    }

    results = dict()

    def setup(self, sfc, userOpts=dict()):
        self.sf = sfc

        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["DOMAIN_NAME", "DOMAIN_NAME_PARENT", "NETBLOCK_OWNER",
                "CO_HOSTED_SITE_DOMAIN", "AFFILIATE_DOMAIN", "SIMILARDOMAIN" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return ["DOMAIN_WHOIS", "NETBLOCK_WHOIS", "DOMAIN_REGISTRAR",
                "CO_HOSTED_SITE_DOMAIN_WHOIS", "AFFILIATE_DOMAIN_WHOIS",
                "SIMILARDOMAIN_WHOIS"]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        if eventData in self.results:
            return None
        else:
            self.results[eventData] = True

        self.sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        try:
            whoisdata = pythonwhois.net.get_whois_raw(eventData)
            data = '\n'.join(whoisdata)
        except BaseException as e:
            self.sf.error("Unable to perform WHOIS on " + eventData + ": " + str(e), False)
            return None

        # Sometimes WHOIS servers refer to another server for more information..
        try:
            for k,v in pythonwhois.parse.parse_raw_whois(whoisdata, True).items():
                if "whois" in k.lower():
                    rawdata = pythonwhois.net.get_whois_raw(eventData, server=v[0])
                    data += "\n" + '\n'.join(rawdata)
        except BaseException as e:
            self.sf.error("Couldn't contact alternative WHOIS server.", False)

        # This is likely to be an error about being throttled rather than real data
        if len(data) < 250:
            self.sf.error("Throttling from Whois is probably happening.", False)
            return None

        if eventName.startswith("DOMAIN_NAME"):
            typ = "DOMAIN_WHOIS"
        if eventName.startswith("NETBLOCK"):
            typ = "NETBLOCK_WHOIS"
        if eventName.startswith("AFFILIATE_DOMAIN"):
            typ = "AFFILIATE_DOMAIN_WHOIS"
        if eventName.startswith("CO_HOSTED_SITE_DOMAIN"):
            typ = "CO_HOSTED_SITE_DOMAIN_WHOIS"
        if eventName == "SIMILARDOMAIN":
            typ = "SIMILARDOMAIN_WHOIS"

        rawevt = SpiderFootEvent(typ, data, self.__name__, event)
        self.notifyListeners(rawevt)

        try:
            info = pythonwhois.parse.parse_raw_whois(whoisdata, True)
            newinfo = {}
            for k, v in info.items():
                newinfo[k.lower()] = v
            info = newinfo
            #print str(info)
        except BaseException as e:
            self.sf.debug("Error parsing whois data for " + eventData)
            return None

        if info.has_key('registrar'):
            if eventName.startswith("DOMAIN_NAME") and info['registrar'] is not None:
                evt = SpiderFootEvent("DOMAIN_REGISTRAR", info['registrar'][0],
                                      self.__name__, event)
                self.notifyListeners(evt)

# End of sfp_whois class
