from unittest.mock import MagicMock, patch

from prefect.logging import disable_run_logger
from prefect.testing.utilities import prefect_test_harness
from prefect import Flow, State
import pytest


@pytest.fixture(autouse=True, scope="session")
def prefect_test_fixture():
    with prefect_test_harness():
        with disable_run_logger():
            yield


@pytest.fixture
def mock_prefect_slack_webhook():
    """Patch the SlackWebhook class to return a mock object."""
    with patch("cpr_sdk.orchestration.hooks.SlackWebhook") as mock_SlackWebhook:
        mock_prefect_slack_block = MagicMock()
        mock_SlackWebhook.load.return_value = mock_prefect_slack_block
        yield mock_SlackWebhook, mock_prefect_slack_block


@pytest.fixture
def mock_flow():
    """Mock Prefect flow object."""
    mock_flow = MagicMock(spec=Flow)
    mock_flow.name = "TestFlow"
    yield mock_flow


@pytest.fixture
def mock_flow_run():
    """Mock Prefect flow run object."""
    mock_flow_run = MagicMock()
    mock_flow_run.name = "TestFlowRun"
    mock_flow_run.id = "test-flow-run-id"
    mock_flow_run.state = MagicMock(spec=State)
    mock_flow_run.state.name = "Completed"
    mock_flow_run.state.message = "message"
    mock_flow_run.state.timestamp = "2025-01-28T12:00:00+00:00"

    yield mock_flow_run
