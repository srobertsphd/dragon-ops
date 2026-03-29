"""
Tests for backup views.
"""

import pytest
from unittest.mock import patch, mock_open
from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from members.views.backups import download_backup_view


@pytest.mark.django_db
class TestDownloadBackupView:
    """Test backup download view."""

    @pytest.fixture
    def staff_user(self, db):
        """Create a staff user for authentication"""
        return User.objects.create_user(
            username="staffuser",
            password="testpass",
            is_staff=True,
        )

    @pytest.fixture
    def regular_user(self, db):
        """Create a regular (non-staff) user"""
        return User.objects.create_user(
            username="regularuser",
            password="testpass",
            is_staff=False,
        )

    @pytest.fixture
    def client(self, staff_user):
        """Create authenticated client with staff user"""
        client = Client()
        client.login(username="staffuser", password="testpass")
        return client

    def test_view_requires_staff_access(self, regular_user):
        """Test view requires staff member access."""
        factory = RequestFactory()
        request = factory.get("/reports/backup-download/")
        request.user = regular_user

        response = download_backup_view(request)

        # Should redirect to login or return 403
        assert response.status_code in [302, 403]

    @patch("members.views.backups.create_backup")
    @patch("members.views.backups.os.path.exists")
    @patch("members.views.backups.os.unlink")
    def test_view_creates_and_downloads_backup(
        self, mock_unlink, mock_exists, mock_create_backup, staff_user
    ):
        """Test view creates backup and downloads it."""
        mock_create_backup.return_value = {
            "success": True,
            "filename": "backup_dev_2025-01-15_14-30-00.json",
            "filepath": "backups/dev/backup_dev_2025-01-15_14-30-00.json",
            "size": 5000,
            "db_type": "dev",
            "error": None,
        }
        mock_exists.return_value = True

        factory = RequestFactory()
        request = factory.get("/reports/backup-download/")
        request.user = staff_user

        # Mock file reading
        with patch("builtins.open", mock_open(read_data=b'{"test": "data"}')):
            response = download_backup_view(request)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        assert "backup_dev_2025-01-15_14-30-00.json" in response["Content-Disposition"]
        assert b'{"test": "data"}' in response.content

        # Verify file was deleted
        mock_unlink.assert_called_once()

    @patch("members.views.backups.create_backup")
    def test_view_handles_backup_failure(self, mock_create_backup, staff_user):
        """Test view handles backup creation failure."""
        mock_create_backup.return_value = {
            "success": False,
            "filename": None,
            "filepath": None,
            "size": None,
            "db_type": "dev",
            "error": "Export failed",
        }

        factory = RequestFactory()
        request = factory.get("/reports/backup-download/")
        request.user = staff_user

        response = download_backup_view(request)

        assert response.status_code == 500
        assert "Backup failed" in response.content.decode()
        assert "Export failed" in response.content.decode()

    @patch("members.views.backups.create_backup")
    @patch("builtins.open")
    def test_view_handles_file_read_error(
        self, mock_open_func, mock_create_backup, staff_user
    ):
        """Test view handles file read errors gracefully."""
        mock_create_backup.return_value = {
            "success": True,
            "filename": "backup_dev_2025-01-15_14-30-00.json",
            "filepath": "backups/dev/backup_dev_2025-01-15_14-30-00.json",
            "size": 5000,
            "db_type": "dev",
            "error": None,
        }
        # Simulate file read error
        mock_open_func.side_effect = IOError("File read error")

        factory = RequestFactory()
        request = factory.get("/reports/backup-download/")
        request.user = staff_user

        with patch("members.views.backups.os.path.exists", return_value=True):
            with patch("members.views.backups.os.unlink") as mock_unlink:
                response = download_backup_view(request)

        assert response.status_code == 500
        assert "Error reading backup file" in response.content.decode()
        # Verify cleanup was attempted
        mock_unlink.assert_called_once()


@pytest.mark.django_db
class TestBackupURLResolution:
    """Test backup URL routes."""

    @pytest.fixture
    def staff_user(self, db):
        """Create a staff user for authentication"""
        return User.objects.create_user(
            username="staffuser",
            password="testpass",
            is_staff=True,
        )

    @pytest.fixture
    def client(self, staff_user):
        """Create authenticated client with staff user"""
        client = Client()
        client.login(username="staffuser", password="testpass")
        return client

    def test_backup_download_url_resolves(self, client):
        """Test that backup download URL resolves correctly."""
        # Mock the create_backup function to avoid actual backup creation
        with patch("members.views.backups.create_backup") as mock_create_backup:
            mock_create_backup.return_value = {
                "success": False,
                "error": "Test error",
            }
            response = client.get("/reports/backup-download/")
            # Should get response (even if error, URL resolved)
            assert response.status_code in [200, 500]

    def test_backup_view_importable(self):
        """Test that backup view can be imported from views module."""
        from members.views import download_backup_view

        assert download_backup_view is not None
        assert callable(download_backup_view)


@pytest.mark.django_db
class TestReportsLandingPageTemplate:
    """Test reports landing page includes backup card."""

    @pytest.fixture
    def staff_user(self, db):
        """Create a staff user for authentication"""
        return User.objects.create_user(
            username="staffuser",
            password="testpass",
            is_staff=True,
        )

    @pytest.fixture
    def client(self, staff_user):
        """Create authenticated client with staff user"""
        client = Client()
        client.login(username="staffuser", password="testpass")
        return client

    def test_reports_landing_page_includes_backup_card(self, client):
        """Test that reports landing page includes Database Backup card."""
        response = client.get("/reports/")
        assert response.status_code == 200
        # Check that backup card elements are present
        assert b"Backup to JSON" in response.content
        assert b"download backup" in response.content.lower()
        # Check that download backup link is present
        assert (
            b"download_backup" in response.content
            or b"backup-download" in response.content
        )
