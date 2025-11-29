# Testing Methodology: pytest + Django

**Created:** November 29, 2025

## Overview

You're using **pytest** as your test framework, NOT Django's built-in test framework. However, you're using Django's **test utilities** (helper classes) which work perfectly with pytest. This is the standard, recommended approach.

## Key Concepts

### 1. pytest is Your Test Framework

**pytest** is the test runner and framework:
- You write test functions (not classes inheriting from `TestCase`)
- You use `assert` statements (not `self.assertEqual()`)
- You use pytest fixtures (`@pytest.fixture`)
- You use pytest markers (`@pytest.mark.django_db`)

### 2. Django Provides Test Utilities (Not a Framework)

Django's `django.test` module provides **helper utilities**, not a test framework:

- **`Client`** - Simulates HTTP requests to your Django views
- **`RequestFactory`** - Creates request objects for testing views
- **`TestCase`** - Django's old test framework (we're NOT using this)

These are just helper classes that work with ANY test framework, including pytest.

### 3. pytest-django Bridges Them

**pytest-django** is a plugin that:
- Integrates pytest with Django's ORM
- Provides the `@pytest.mark.django_db` decorator
- Provides the `db` fixture for database access
- Handles Django settings configuration

## What You're Actually Using

### ✅ pytest Framework (What You Wanted)
```python
import pytest

@pytest.mark.django_db
def test_something(db):
    # This is pytest!
    assert something == expected
```

### ✅ Django Test Utilities (Helper Classes)
```python
from django.test import Client  # Just a helper class

def test_view(client):
    response = client.get('/some-url/')
    assert response.status_code == 200
```

### ❌ NOT Using Django's TestCase
```python
# We're NOT doing this:
from django.test import TestCase

class MyTest(TestCase):  # Old Django way
    def setUp(self):
        ...
    def test_something(self):
        self.assertEqual(...)
```

## Why This Mix?

### Django's Test Utilities Are Just Helper Classes

Think of Django's test utilities like any other library:

```python
# These are just helper classes, not a test framework:
from django.test import Client          # Like: from requests import Session
from django.test import RequestFactory  # Like: from datetime import datetime

# You use them WITH pytest:
def test_my_view(client):
    response = client.get('/url/')  # Client is just a helper
    assert response.status_code == 200  # pytest assertion
```

### You Can't Avoid Django Utilities

Django's `Client` and `RequestFactory` are the **standard way** to test Django views:

- **`Client`** - The only way to simulate HTTP requests in Django
- **`RequestFactory`** - The only way to create request objects for view testing
- **Django ORM** - The only way to interact with your database models

These aren't part of a test framework - they're Django's testing API.

## Comparison: Old Django Way vs pytest Way

### Old Django Way (TestCase)
```python
from django.test import TestCase

class MyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.client = Client()
    
    def test_view(self):
        self.client.force_login(self.user)
        response = self.client.get('/url/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'expected text')
```

### pytest Way (What You're Using)
```python
import pytest
from django.test import Client

@pytest.fixture
def user(db):
    return User.objects.create_user(...)

@pytest.fixture
def client(user):
    c = Client()
    c.force_login(user)
    return c

def test_view(client):
    response = client.get('/url/')
    assert response.status_code == 200
    assert 'expected text' in response.content.decode()
```

## Key Differences

| Aspect | Django TestCase | pytest (What You're Using) |
|--------|----------------|---------------------------|
| **Test Framework** | Django's TestCase | pytest |
| **Test Structure** | Classes with methods | Functions |
| **Assertions** | `self.assertEqual()` | `assert` statements |
| **Setup** | `setUp()` method | `@pytest.fixture` |
| **Database** | Automatic transactions | `@pytest.mark.django_db` |
| **Django Utilities** | ✅ Uses Client, RequestFactory | ✅ Uses Client, RequestFactory |
| **Test Discovery** | Django's test runner | pytest discovery |

## What Makes It "pytest"?

You're using pytest because:

1. ✅ **Test functions** (not TestCase classes)
2. ✅ **pytest fixtures** (`@pytest.fixture`)
3. ✅ **pytest markers** (`@pytest.mark.django_db`)
4. ✅ **pytest assertions** (`assert` statements)
5. ✅ **pytest test discovery** (finds `test_*.py` files)
6. ✅ **pytest CLI** (`pytest tests/`)

## What Makes It "Django"?

You're using Django utilities because:

1. ✅ **Django ORM** - `Member.objects.create()`
2. ✅ **Django Client** - `Client().get('/url/')`
3. ✅ **Django RequestFactory** - `RequestFactory().get()`
4. ✅ **Django models** - `Member`, `Payment`, etc.

These are Django's APIs for testing, not a test framework.

## The Standard Approach

This is the **recommended approach** for Django + pytest:

1. **Use pytest** as your test framework
2. **Use pytest-django** plugin for Django integration
3. **Use Django's test utilities** (Client, RequestFactory) - they're just helper classes
4. **Use pytest fixtures** instead of setUp methods
5. **Use pytest markers** for database access

## Example: Your Current Tests

```python
# This is 100% pytest:
import pytest
from django.test import Client  # Just a helper class

@pytest.mark.django_db  # pytest-django marker
@pytest.fixture  # pytest fixture
def client(db, staff_user):  # pytest fixtures
    client = Client()  # Django helper class
    client.force_login(staff_user)
    return client

def test_view(client):  # pytest test function
    response = client.get('/url/')  # Django Client helper
    assert response.status_code == 200  # pytest assertion
```

## Could You Avoid Django Utilities?

**No, not really:**

- **Testing views?** → Need `Client` or `RequestFactory` (Django's only way)
- **Testing models?** → Need Django ORM (Django's only way)
- **Testing forms?** → Need Django form classes (Django's only way)

These are Django's APIs, not a test framework choice.

## Summary

- ✅ **You ARE using pytest** - it's your test framework
- ✅ **Django utilities are just helpers** - like any library (requests, datetime, etc.)
- ✅ **pytest-django bridges them** - makes Django work with pytest
- ✅ **This is the standard approach** - recommended by Django and pytest communities

**Think of it this way:**
- pytest = Your test framework (like unittest, nose, etc.)
- Django utilities = Helper classes (like requests.Session, datetime.datetime)
- pytest-django = Integration plugin (makes them work together)

You're not mixing test frameworks - you're using pytest with Django's helper utilities!

