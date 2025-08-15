"""Hello unit test module."""

from src.hello import hello


def test_hello():
    """Test the hello function."""
    assert hello() == "Hello sistema-unidad-territorial/backend"
