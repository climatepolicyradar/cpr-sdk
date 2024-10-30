import os
import json
import tempfile
from pathlib import Path

import boto3
import pytest
from moto import mock_aws
from typing import Generator

from cpr_sdk.search_adaptors import VespaSearchAdapter

VESPA_TEST_SEARCH_URL = "http://localhost:8080"


@pytest.fixture()
def test_vespa():
    """Vespa adapter pointing to test url and using empty cert files"""
    with tempfile.TemporaryDirectory() as tmpdir_cert_dir:
        with open(Path(tmpdir_cert_dir) / "cert.pem", "w"):
            pass
        with open(Path(tmpdir_cert_dir) / "key.pem", "w"):
            pass
        adaptor = VespaSearchAdapter(
            instance_url=VESPA_TEST_SEARCH_URL, cert_directory=tmpdir_cert_dir
        )

        yield adaptor


@pytest.fixture()
def s3_client():
    with mock_aws():
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="test-bucket")
        s3_client.put_object(
            Bucket="test-bucket", Key="test-prefix/test1.txt", Body="test1 text"
        )
        s3_client.put_object(
            Bucket="test-bucket", Key="test-prefix/subdir/test2.txt", Body="test2 text"
        )
        s3_client.put_object(
            Bucket="test-bucket",
            Key="test-wrongprefix/subdir/test3.txt",
            Body="test3 text",
        )

        for file in Path("tests/test_data/valid").glob("*.json"):
            s3_client.put_object(
                Bucket="test-bucket",
                Key=f"embeddings_input/{file.name}",
                Body=file.read_text(),
            )

        s3_client.create_bucket(Bucket="empty-bucket")

        yield s3_client


@pytest.fixture()
def parser_output_json_pdf() -> dict:
    """A dictionary representation of a parser output"""
    with open("tests/test_data/valid/test_pdf.json") as f:
        return json.load(f)


@pytest.fixture()
def parser_output_json_html() -> dict:
    """A dictionary representation of a parser output"""
    with open("tests/test_data/valid/test_html.json") as f:
        return json.load(f)


@pytest.fixture()
def parser_output_json_flat() -> dict:
    """A dictionary representation of a parser output that is flat"""
    with open("tests/test_data/huggingface/flat_hf_parser_output.json") as f:
        return json.load(f)


@pytest.fixture()
def backend_document_json() -> dict:
    """A dictionary representation of a backend document"""
    return {
        "name": "test_name",
        "description": "test_description",
        "import_id": "test_import_id",
        "slug": "test_slug",
        "family_import_id": "test_family_import_id",
        "family_slug": "test_family_slug",
        "publication_ts": "2021-01-01T00:00:00+00:00",
        "date": "01/01/2021",
        "source_url": "test_source_url",
        "download_url": "test_download_url",
        "type": "test_type",
        "source": "test_source",
        "category": "test_category",
        "geography": "test_geography",
        "languages": ["test_language"],
        "metadata": {"test_metadata": "test_value"},
    }


@pytest.fixture(scope="function")
def mock_aws_creds() -> None:
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["AWS_SECURITY_TOKEN"] = "test"
    os.environ["AWS_SESSION_TOKEN"] = "test"


@pytest.fixture(scope="function")
def mock_ssm_client(mock_aws_creds) -> Generator:
    """Mocked SSM client."""
    with mock_aws():
        yield boto3.client("ssm", region_name="eu-west-1")


@pytest.fixture()
def mock_vespa_credentials() -> dict[str, str]:
    """Mock Vespa credentials."""
    return {
        "VESPA_INSTANCE_URL": "http://localhost:8080",
        "VESPA_PUBLIC_CERT": "Cert Content",
        "VESPA_PRIVATE_KEY": "Key Content",
    }


@pytest.fixture
def create_vespa_params(mock_ssm_client, mock_vespa_credentials) -> None:
    """Create Vespa parameters in SSM."""
    mock_ssm_client.put_parameter(
        Name="VESPA_INSTANCE_URL",
        Description="A test parameter for the vespa instance.",
        Value=mock_vespa_credentials["VESPA_INSTANCE_URL"],
        Type="SecureString",
    )
    mock_ssm_client.put_parameter(
        Name="VESPA_PUBLIC_CERT",
        Description="A test parameter for a vespa public cert",
        Value=mock_vespa_credentials["VESPA_PUBLIC_CERT"],
        Type="SecureString",
    )
    mock_ssm_client.put_parameter(
        Name="VESPA_PRIVATE_KEY",
        Description="A test parameter for a vespa private key",
        Value=mock_vespa_credentials["VESPA_PRIVATE_KEY"],
        Type="SecureString",
    )
