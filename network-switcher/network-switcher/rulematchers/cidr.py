def add_match_rule(callback, match_value):
    if type(match_value) != list:
        match_value = [match_value]
    for cidr in match_value:
        callback("-d %s" % cidr)
