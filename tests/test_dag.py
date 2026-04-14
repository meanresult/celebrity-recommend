"""
Airflow DAG 구조 검증 테스트

DAG import 오류, task 존재 여부, 의존성 순서를 확인.
실제 DB/Snowflake 연결 없이 실행 가능.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestDagStructure:
    """DAG 파일이 올바르게 정의되어 있는지 검증"""

    @pytest.fixture(scope="class")
    def dag_bag(self):
        """DagBag 로드 — import 오류 여부 포함"""
        from airflow.models import DagBag
        return DagBag(
            dag_folder=os.path.join(os.path.dirname(__file__), "../dags"),
            include_examples=False,
        )

    def test_no_import_errors(self, dag_bag):
        """DAG 파일에 import 오류가 없어야 한다"""
        assert dag_bag.import_errors == {}, \
            f"DAG import errors:\n{dag_bag.import_errors}"

    def test_dag_exists(self, dag_bag):
        """insta_to_snowflake DAG 가 존재해야 한다"""
        assert "insta_to_snowflake" in dag_bag.dag_ids, \
            f"등록된 DAG 목록: {list(dag_bag.dag_ids)}"

    def test_required_tasks_exist(self, dag_bag):
        """extract, load task 가 모두 정의되어 있어야 한다"""
        dag = dag_bag.get_dag("insta_to_snowflake")
        task_ids = {task.task_id for task in dag.tasks}

        assert "extract_instagram_data" in task_ids
        assert "load_to_snowflake" in task_ids

    def test_task_dependency_order(self, dag_bag):
        """extract → load 순서여야 한다"""
        dag = dag_bag.get_dag("insta_to_snowflake")
        tasks = {task.task_id: task for task in dag.tasks}

        load_task = tasks["load_to_snowflake"]
        upstream_ids = {t.task_id for t in load_task.upstream_list}
        assert "extract_instagram_data" in upstream_ids, \
            "load_to_snowflake 는 extract_instagram_data 다음에 실행되어야 한다"
