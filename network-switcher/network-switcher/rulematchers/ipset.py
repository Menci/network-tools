def add_match_rule(callback, match_value):
    callback("-m set --match-set %s dst" % match_value)
