"""Executed by the Chaquopy runtime in the installed Android APK."""

def greet(value):
    assert isinstance(value, int)
    result = value * 2 + 1
    assert result == 7
    return f"PYTHAN EYE IDE\n\nPYTHON APK TEST PASSED\n\n3 * 2 + 1 = {result}\n\nVEER CREATION"
