import os

from prefect.settings import PREFECT_UI_URL
from prefect_slack.credentials import SlackWebhook


class SlackNotify:
    """Notify a Slack channel through a Prefect Slack webhook."""

    # Message templates
    FLOW_RUN_URL = "{prefect_base_url}/flow-runs/flow-run/{flow_run.id}"
    BASE_MESSAGE = (
        "Flow run {flow.name}/{flow_run.name} observed in "
        "state `{flow_run.state.name}` at {flow_run.state.timestamp}. "
        "For environment: {environment}. "
        "Flow run URL: {ui_url}. "
        "State message: {state.message}"
    )

    def __init__(self, slack_block_name):
        self.slack = SlackWebhook.load(slack_block_name)
        self.environment = os.getenv("AWS_ENV", "sandbox")

    def message(self, flow, flow_run, state):
        """
        Send a notification to a Slack channel about the state of a Prefect flow run.

        Intended to be called from prefect flow hooks:

        ```python
        @flow(on_failure=[SlackNotify(slack_block_name).message])
        def my_flow():
            pass
        ```
        """

        ui_url = self.FLOW_RUN_URL.format(
            prefect_base_url=PREFECT_UI_URL.value(), flow_run=flow_run
        )
        msg = self.BASE_MESSAGE.format(
            flow=flow,
            flow_run=flow_run,
            state=state,
            ui_url=ui_url,
            environment=self.environment,
        )
        self.send(msg)

    def send(self, msg: str):
        """Send a message to a Slack channel."""
        self.slack.notify(body=msg)
