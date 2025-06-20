import json

LIMITS_FILE = 'limits.json'

def load_limits():
    try:
        with open(LIMITS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_limits(limits):
    with open(LIMITS_FILE, 'w') as file:
        json.dump(limits, file)
