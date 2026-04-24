import json

LIMITS_FILE = 'limits.json'

DEFAULT_UPPER = 2.2
DEFAULT_LOWER = 1.8

# Defaults for the global graph display range (Y-axis of all charts)
GRAPH_DEFAULT_LOWER = 0.0
GRAPH_DEFAULT_UPPER = 5.0


def load_limits():
    try:
        with open(LIMITS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_limits(limits):
    with open(LIMITS_FILE, 'w') as file:
        json.dump(limits, file)


def load_graph_limits():
    """Return the global graph display limits (min/max for the chart Y-axis)."""
    data = load_limits()
    graph = data.get('graph', {})
    return {
        'lower': graph.get('lower', GRAPH_DEFAULT_LOWER),
        'upper': graph.get('upper', GRAPH_DEFAULT_UPPER),
    }


def save_graph_limits(lower, upper):
    """Persist the global graph display limits without touching machine alert limits."""
    data = load_limits()
    data['graph'] = {'lower': float(lower), 'upper': float(upper)}
    save_limits(data)


def clamp(value, lower, upper):
    """Clamp *value* to [lower, upper]. Returns None if value is None."""
    if value is None:
        return None
    return max(lower, min(upper, value))
