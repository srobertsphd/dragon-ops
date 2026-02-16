"""
Tests for CSV backup export view and downloads.
"""

import io
import zipfile

import pytest
from django.test import Client
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestCsvBackupExportView:
    """Test CSV backup export page and downloads."""

    @pytest.fixture
    def staff_user(self, db):
        return User.objects.create_user(
            username="staffuser",
            password="testpass",
            is_staff=True,
        )

    @pytest.fixture
    def regular_user(self, db):
        return User.objects.create_user(
            username="regularuser",
            password="testpass",
            is_staff=False,
        )

    @pytest.fixture
    def client(self, staff_user):
        c = Client()
        c.login(username="staffuser", password="testpass")
        return c

    def test_staff_can_open_csv_backup_page(self, client):
        """Staff GET /reports/csv-backup/ returns 200 and schema in HTML."""
        response = client.get("/reports/csv-backup/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "member_types" in content
        assert "members.csv" in content

    def test_non_staff_cannot_open_csv_backup_page(self, regular_user):
        """Non-staff GET /reports/csv-backup/ returns 302 or 403."""
        c = Client()
        c.login(username="regularuser", password="testpass")
        response = c.get("/reports/csv-backup/")
        assert response.status_code in [302, 403]

    def test_download_zip_returns_zip_with_csvs_and_schema(self, client):
        """GET ?download=zip returns ZIP with four CSVs and schema JSON."""
        response = client.get("/reports/csv-backup/", {"download": "zip"})
        assert response.status_code == 200
        assert "application/zip" in response.get("Content-Type", "")
        assert ".zip" in response.get("Content-Disposition", "")
        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zf:
            names = zf.namelist()
        assert set(names) == {
            "member_types.csv",
            "payment_methods.csv",
            "members.csv",
            "payments.csv",
            "csv_export_schema.json",
        }
        assert len(names) == 5
        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zf:
            schema_content = zf.read("csv_export_schema.json").decode()
        assert "member_id" in schema_content
        assert "member_types" in schema_content
