import pytest

from db_support import require_test_database


@pytest.mark.parametrize("url", [
    "postgresql://localhost/agniview",
    "postgresql://localhost/postgres",
    "postgresql://localhost/test",
    "postgresql://localhost/agniview_test?dbname=agniview",
    "postgresql://localhost/agniview_test#ignored",
    "dbname=agniview_test service=production",
    "postgresql://localhost/agniview_test/agniview",
])
def test_rejects_unsafe_database_before_connecting(url):
    with pytest.raises(ValueError, match="dedicated"):
        require_test_database(url)


@pytest.mark.parametrize("name", ["agniview_test", "agniview_test_migrations"])
def test_accepts_explicit_test_database(name):
    assert require_test_database(f"postgresql://localhost/{name}") == name


def test_rejects_connection_resolved_to_another_database():
    with pytest.raises(ValueError, match="dedicated"):
        require_test_database("postgresql://localhost/agniview_test", actual_name="agniview")
