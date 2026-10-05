"""Red fixture for SG104: banned tokens (TODO, FIXME, XXX, @skip, skipTest, expectedFailure)."""


def incomplete_function():
    # TODO: implement this function
    pass


def another_function():
    # FIXME: this is broken
    return None


# XXX: dangerous code ahead
dangerous_code = True


@unittest.skip("skipped test")
def test_something():
    pass
