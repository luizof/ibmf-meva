import json

LIMITS_FILE = 'limits.json'

DEFAULT_UPPER = 2.2
DEFAULT_LOWER = 1.8

def load_limits():
    try:
        with open(LIMITS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_limits(limits):
    with open(LIMITS_FILE, 'w') as file:
        json.dump(limits, file)
