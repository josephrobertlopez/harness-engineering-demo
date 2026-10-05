"""Green fixture for SG103: vulture - no dead code."""


def process_data():
    used_var = 10
    print(used_var)
    return used_var
