"""
Unit tests for BaseManager to ensure all query methods return dataclass objects and not ORM objects, preventing DetachedInstanceError.
"""

import pytest
from airunner.data.models.base_manager import BaseManager
from airunner.data.models.user import User
from airunner.data.session_manager import session_scope
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="module")
def user_manager():
    return BaseManager(User)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Clean up users before each test
    with session_scope() as session:
        session.query(User).delete()
        session.commit()
    yield
    with session_scope() as session:
        session.query(User).delete()
        session.commit()


def test_create_and_get_returns_dataclass(user_manager):
    user = user_manager.create(username="TestUser", zipcode="12345")
    assert hasattr(user, "username")
    assert user.username == "TestUser"
    # get should return dataclass, not ORM
    got = user_manager.get(user.id)
    assert hasattr(got, "username")
    assert got.username == "TestUser"
    # Should not raise DetachedInstanceError
    assert got.__class__.__name__.endswith("Data")


def test_all_returns_list_of_dataclasses(user_manager):
    user_manager.create(username="A", zipcode="1")
    user_manager.create(username="B", zipcode="2")
    all_users = user_manager.all()
    assert isinstance(all_users, list)
    assert all_users
    for u in all_users:
        assert hasattr(u, "username")
        assert u.__class__.__name__.endswith("Data")


def test_filter_by_returns_dataclasses(user_manager):
    user_manager.create(username="FilterMe", zipcode="99999")
    filtered = user_manager.filter_by(username="FilterMe")
    assert isinstance(filtered, list)
    assert filtered
    for u in filtered:
        assert u.username == "FilterMe"
        assert u.__class__.__name__.endswith("Data")


def test_first_and_filter_first(user_manager):
    user_manager.create(username="FirstGuy", zipcode="11111")
    first = user_manager.first()
    assert hasattr(first, "username")
    assert first.__class__.__name__.endswith("Data")
    filter_first = user_manager.filter_first(User.username == "FirstGuy")
    assert filter_first.username == "FirstGuy"
    assert filter_first.__class__.__name__.endswith("Data")
