import json
import logging
import re
from os import environ
from apluslms_yamlidator.document import find_ml

logger = logging.getLogger(__name__)
json_re = re.compile(r'^(?:["[{]|(?:-?[1-9]\d*(?:\.\d+)?|null|true|false)$)')


def nest_dict(flat_dict):
    nested = {}
    for keys, value in flat_dict.items():
        dict_, key = find_ml(nested, keys, create_dicts=True)
        dict_[key] = value
    return nested


def load_from_env(env_prefix=None, decode_json=True):
    if decode_json:
        decode = lambda s: json.loads(s) if json_re.match(s) is not None else s
    else:
        decode = lambda s: s
    env = {key[len(env_prefix):].lower(): decode(value) for key, value in environ.items() if key.startswith(env_prefix)}
    return nest_dict(env)
