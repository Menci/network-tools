from . import cidr
from . import ipset
from . import raw

matchers = {}

matchers["cidr"] = cidr.add_match_rule
matchers["ipset"] = ipset.add_match_rule
matchers["raw"] = raw.add_match_rule

def add_match_rule(callback, match, match_value):
    matchers[match](callback, match_value)
