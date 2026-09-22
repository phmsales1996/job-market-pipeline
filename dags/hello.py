from airflow.sdk import dag, task

@dag(schedule=None)
def my_first_dag():

    @task
    def first_task():
        print("First")

    @task
    def second_task():
        print("Second")

    first_task() >> second_task()

my_first_dag()