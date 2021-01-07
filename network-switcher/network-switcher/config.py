import yaml

import utils

def load(config_file):
    return yaml.safe_load(open(config_file).read())
