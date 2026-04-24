import json

LIMITS_FILE = 'limits.json'

DEFAULT_UPPER = 2.2
DEFAULT_LOWER = 1.8

# Defaults for the global graph display range (Y-axis of all charts)
GRAPH_DEFAULT_LOWER = 0.0
GRAPH_DEFAULT_UPPER = 5.0

# Default smoothing (moving average) setting
SMOOTHING_DEFAULT_ENABLED = False
SMOOTHING_DEFAULT_SECONDS = 30

# Reserved top-level keys in limits.json that are NOT machine ids
_RESERVED_KEYS = {'graph', 'smoothing'}


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


def get_machine_graph_limits(machine_id, data=None):
    """Return the graph display limits for a given machine, falling back to global.

    If ``data`` is provided, it is used instead of loading from disk (useful when
    iterating over many machines in a single request).
    """
    if data is None:
        data = load_limits()
    machine_entry = data.get(str(machine_id), {}) if isinstance(data.get(str(machine_id)), dict) else {}
    global_graph = data.get('graph', {})
    lower = machine_entry.get('graph_lower')
    upper = machine_entry.get('graph_upper')
    if lower is None:
        lower = global_graph.get('lower', GRAPH_DEFAULT_LOWER)
    if upper is None:
        upper = global_graph.get('upper', GRAPH_DEFAULT_UPPER)
    return {'lower': float(lower), 'upper': float(upper)}


def load_smoothing():
    """Return the current global smoothing (moving average) setting."""
    data = load_limits()
    smoothing = data.get('smoothing', {})
    return {
        'enabled': bool(smoothing.get('enabled', SMOOTHING_DEFAULT_ENABLED)),
        'seconds': int(smoothing.get('seconds', SMOOTHING_DEFAULT_SECONDS)),
    }


def save_smoothing(enabled, seconds):
    """Persist the global smoothing setting."""
    data = load_limits()
    data['smoothing'] = {
        'enabled': bool(enabled),
        'seconds': max(1, int(seconds)),
    }
    save_limits(data)


def clamp(value, lower, upper):
    """Clamp *value* to [lower, upper]. Returns None if value is None."""
    if value is None:
        return None
    return max(lower, min(upper, value))
