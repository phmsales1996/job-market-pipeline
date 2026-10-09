"""The names two DAGs agree on.

An Airflow asset is only a name: one DAG says "this was updated" (an outlet), another is
scheduled on it. If the two sides spelled the name differently, nothing would fail - the
listening DAG would simply never run. So each name is written once, here, and imported by both.
"""
from airflow.sdk import Asset

SOURCES = ["greenhouse", "lever", "ashby", "recruitee", "teamtailor", "workable"]

# Announced by the last task of each ingestion DAG when its nightly run is over, whether the
# run succeeded or failed. The transform DAG waits for all six.
INGESTION_FINISHED = {source: Asset(f"ingestion_finished/{source}") for source in SOURCES}
