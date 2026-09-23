import logging

logger = logging.getLogger(__name__)

def build_alert(dag_id, task_id, ds, run_id, try_number, exception):
    return f"Dag_id: {dag_id}. Task_id: {task_id}. Ds: {ds}. Run_id: {run_id}. Try_number: {try_number}. Exception: {exception}. See RUNBOOK.md."

def alert_on_failure(context):
    dag_id = context["ti"].dag_id
    task_id = context["ti"].task_id
    try_number = context["ti"].try_number
    ds = context.get("ds")
    run_id = context.get("run_id")
    exception = context.get("exception")
    logger.error(build_alert(dag_id, task_id, ds, run_id, try_number, exception))