# Green case: proper AC test coverage with marker and assertions

# covers: AC-1
def test_validate_input_success():
    """Test that properly covers AC-1 with assertions."""
    from src import validate_input

    result = validate_input("data")
    assert result is True, "Should return True for valid data"
