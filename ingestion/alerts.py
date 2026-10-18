import logging
import os

import requests

logger = logging.getLogger(__name__)

def build_alert(dag_id, task_id, ds, run_id, try_number, exception):
    return f"Dag_id: {dag_id}. Task_id: {task_id}. Ds: {ds}. Run_id: {run_id}. Try_number: {try_number}. Exception: {exception}. See RUNBOOK.md."

def ping(suffix="", message=""):
    # Healthchecks.io emails on a "/fail" ping, and when the plain ping has not arrived in time.
    # Optional on purpose: unset (local runs) means no ping, and an unreachable endpoint is logged,
    # never raised - an alert must not fail the task it reports on.
    url = os.environ.get("HEALTHCHECK_URL")
    if not url:
        return
    try:
        requests.post(url + suffix, data=message.encode(), timeout=10)
    except requests.RequestException:
        logger.exception("Could not reach the healthcheck endpoint.")

def alert_on_failure(context):
    dag_id = context["ti"].dag_id
    task_id = context["ti"].task_id
    try_number = context["ti"].try_number
    ds = context.get("ds")
    run_id = context.get("run_id")
    exception = context.get("exception")
    alert = build_alert(dag_id, task_id, ds, run_id, try_number, exception)
    logger.error(alert)
    ping("/fail", alert)
