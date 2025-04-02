from cpr_sdk.orchestration.hooks import SlackNotify


def test_message(mock_prefect_slack_webhook, mock_flow, mock_flow_run):
    slack_block = "slack-webhook-platform-prefect-mvp-sandbox"

    SlackNotify(slack_block).message(mock_flow, mock_flow_run, mock_flow_run.state)
    mock_SlackWebhook, mock_prefect_slack_block = mock_prefect_slack_webhook

    # `.load`
    mock_SlackWebhook.load.assert_called_once_with(slack_block)

    # `.notify`
    mock_prefect_slack_block.notify.assert_called_once()
    kwargs = mock_prefect_slack_block.notify.call_args.kwargs
    message = kwargs.get("body", "")
    assert message == (
        "Flow run TestFlow/TestFlowRun observed in state `Completed` at "
        "2025-01-28T12:00:00+00:00. For environment: sandbox. Flow run URL: "
        "None/flow-runs/flow-run/test-flow-run-id. State message: message"
    )
