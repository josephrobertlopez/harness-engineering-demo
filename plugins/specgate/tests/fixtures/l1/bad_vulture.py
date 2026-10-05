"""Red fixture for SG103: vulture - unused variable."""


def process_data():
    used_var = 10
    unused_var = 20  # This will be flagged by vulture
    print(used_var)
    return used_var
