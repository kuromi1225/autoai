"""
Parallel Task Executor - 並列タスク実行エンジン

このモジュールは、Celeryを使用してタスクの並列実行を管理し、
依存関係を考慮した効率的なタスク実行を提供します。
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import json
from celery import Celery, group, chain, chord
from celery.result import GroupResult, AsyncResult
import redis

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"

@dataclass
class TaskExecution:
    """タスク実行情報"""
    task_id: str
    celery_task_id: str
    status: ExecutionStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class ParallelGroup:
    """並列実行グループ"""
    group_id: str
    task_ids: List[str]
    celery_group_id: str
    status: ExecutionStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: Dict[str, Any] = None

class ParallelTaskExecutor:
    """
    並列タスク実行エンジン
    
    機能:
    - Celeryを使用した並列タスク実行
    - 依存関係を考慮した実行順序制御
    - リアルタイム進捗監視
    - エラーハンドリングと自動リトライ
    - リソース使用量の最適化
    """
    
    def __init__(self, celery_app: Celery, redis_client: redis.Redis):
        """
        並列タスク実行エンジンを初期化
        
        Args:
            celery_app: Celeryアプリケーションインスタンス
            redis_client: Redisクライアント
        """
        self.celery_app = celery_app
        self.redis_client = redis_client
        self.executions: Dict[str, TaskExecution] = {}
        self.parallel_groups: Dict[str, ParallelGroup] = {}
        
        # 実行統計
        self.execution_stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'parallel_groups_executed': 0,
            'total_time_saved': 0
        }
    
    def execute_parallel_workflow(
        self, 
        task_nodes: List[Any], 
        parallel_analysis: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        並列ワークフローを実行
        
        Args:
            task_nodes: 実行するタスクノードのリスト
            parallel_analysis: 並列実行分析結果
            progress_callback: 進捗コールバック関数
            
        Returns:
            実行結果の辞書
        """
        try:
            logger.info(f"Starting parallel workflow execution with {len(task_nodes)} tasks")
            
            workflow_id = f"workflow_{datetime.utcnow().timestamp()}"
            start_time = datetime.utcnow()
            
            # 並列グループを順次実行
            results = {}
            total_levels = len(parallel_analysis['parallel_groups'])
            
            for level_index, group_info in enumerate(parallel_analysis['parallel_groups']):
                level_results = self._execute_parallel_group(
                    group_info, 
                    task_nodes,
                    progress_callback
                )
                
                results.update(level_results)
                
                # 進捗報告
                if progress_callback:
                    progress = (level_index + 1) / total_levels * 100
                    progress_callback({
                        'workflow_id': workflow_id,
                        'progress': progress,
                        'current_level': level_index + 1,
                        'total_levels': total_levels,
                        'completed_tasks': len([r for r in results.values() if r.get('status') == 'success']),
                        'failed_tasks': len([r for r in results.values() if r.get('status') == 'failure'])
                    })
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            # 実行統計を更新
            self._update_execution_stats(results, execution_time, parallel_analysis)
            
            return {
                'workflow_id': workflow_id,
                'status': 'completed',
                'execution_time': execution_time,
                'results': results,
                'statistics': self.execution_stats.copy()
            }
            
        except Exception as e:
            logger.error(f"Parallel workflow execution failed: {e}")
            return {
                'workflow_id': workflow_id,
                'status': 'failed',
                'error': str(e),
                'results': results if 'results' in locals() else {}
            }
    
    def _execute_parallel_group(
        self, 
        group_info: Dict[str, Any], 
        task_nodes: List[Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """並列グループを実行"""
        
        group_id = f"group_{datetime.utcnow().timestamp()}"
        task_ids = group_info['task_ids']
        
        logger.info(f"Executing parallel group {group_id} with {len(task_ids)} tasks")
        
        # タスクノードを取得
        group_tasks = [node for node in task_nodes if node.id in task_ids]
        
        if len(group_tasks) == 1:
            # 単一タスクの場合
            return self._execute_single_task(group_tasks[0])
        else:
            # 複数タスクの並列実行
            return self._execute_multiple_tasks_parallel(group_tasks, group_id)
    
    def _execute_single_task(self, task_node: Any) -> Dict[str, Any]:
        """単一タスクを実行"""
        
        try:
            logger.info(f"Executing single task: {task_node.id}")
            
            # Celeryタスクを作成・実行
            celery_task = self._create_celery_task(task_node)
            result = celery_task.apply_async()
            
            # 実行情報を記録
            execution = TaskExecution(
                task_id=task_node.id,
                celery_task_id=result.id,
                status=ExecutionStatus.RUNNING,
                start_time=datetime.utcnow()
            )
            self.executions[task_node.id] = execution
            
            # 結果を待機
            task_result = result.get(timeout=task_node.estimated_time * 60)
            
            # 実行完了
            execution.status = ExecutionStatus.SUCCESS
            execution.end_time = datetime.utcnow()
            execution.result = task_result
            
            return {
                task_node.id: {
                    'status': 'success',
                    'result': task_result,
                    'execution_time': (execution.end_time - execution.start_time).total_seconds()
                }
            }
            
        except Exception as e:
            logger.error(f"Single task execution failed for {task_node.id}: {e}")
            
            if task_node.id in self.executions:
                self.executions[task_node.id].status = ExecutionStatus.FAILURE
                self.executions[task_node.id].error = str(e)
                self.executions[task_node.id].end_time = datetime.utcnow()
            
            return {
                task_node.id: {
                    'status': 'failure',
                    'error': str(e)
                }
            }
    
    def _execute_multiple_tasks_parallel(
        self, 
        task_nodes: List[Any], 
        group_id: str
    ) -> Dict[str, Any]:
        """複数タスクを並列実行"""
        
        try:
            logger.info(f"Executing {len(task_nodes)} tasks in parallel (group: {group_id})")
            
            # Celeryグループを作成
            celery_tasks = []
            for task_node in task_nodes:
                celery_task = self._create_celery_task(task_node)
                celery_tasks.append(celery_task)
                
                # 実行情報を記録
                execution = TaskExecution(
                    task_id=task_node.id,
                    celery_task_id="",  # グループ実行後に設定
                    status=ExecutionStatus.PENDING,
                    start_time=datetime.utcnow()
                )
                self.executions[task_node.id] = execution
            
            # グループ実行
            job = group(celery_tasks)
            group_result = job.apply_async()
            
            # 並列グループ情報を記録
            parallel_group = ParallelGroup(
                group_id=group_id,
                task_ids=[node.id for node in task_nodes],
                celery_group_id=group_result.id,
                status=ExecutionStatus.RUNNING,
                start_time=datetime.utcnow()
            )
            self.parallel_groups[group_id] = parallel_group
            
            # 結果を待機
            max_timeout = max(node.estimated_time for node in task_nodes) * 60
            results = group_result.get(timeout=max_timeout)
            
            # 結果を処理
            task_results = {}
            for i, (task_node, result) in enumerate(zip(task_nodes, results)):
                execution = self.executions[task_node.id]
                execution.status = ExecutionStatus.SUCCESS
                execution.end_time = datetime.utcnow()
                execution.result = result
                
                task_results[task_node.id] = {
                    'status': 'success',
                    'result': result,
                    'execution_time': (execution.end_time - execution.start_time).total_seconds()
                }
            
            # 並列グループ完了
            parallel_group.status = ExecutionStatus.SUCCESS
            parallel_group.end_time = datetime.utcnow()
            parallel_group.results = task_results
            
            return task_results
            
        except Exception as e:
            logger.error(f"Parallel group execution failed for {group_id}: {e}")
            
            # エラー処理
            error_results = {}
            for task_node in task_nodes:
                if task_node.id in self.executions:
                    self.executions[task_node.id].status = ExecutionStatus.FAILURE
                    self.executions[task_node.id].error = str(e)
                    self.executions[task_node.id].end_time = datetime.utcnow()
                
                error_results[task_node.id] = {
                    'status': 'failure',
                    'error': str(e)
                }
            
            if group_id in self.parallel_groups:
                self.parallel_groups[group_id].status = ExecutionStatus.FAILURE
                self.parallel_groups[group_id].end_time = datetime.utcnow()
            
            return error_results
    
    def _create_celery_task(self, task_node: Any):
        """タスクノードからCeleryタスクを作成"""
        
        # タスクタイプに基づいてCeleryタスクを選択
        task_mapping = {
            'coding': 'execute_coding_task',
            'testing': 'execute_testing_task',
            'research': 'execute_research_task',
            'documentation': 'execute_documentation_task',
            'deployment': 'execute_deployment_task',
            'debugging': 'execute_debugging_task'
        }
        
        task_name = task_mapping.get(task_node.task_type.value, 'execute_generic_task')
        
        # タスクパラメータを準備
        task_params = {
            'task_id': task_node.id,
            'title': task_node.title,
            'description': task_node.description,
            'task_type': task_node.task_type.value,
            'tools': task_node.tools,
            'acceptance_criteria': task_node.acceptance_criteria,
            'estimated_time': task_node.estimated_time,
            'complexity': task_node.complexity
        }
        
        return self.celery_app.signature(task_name, args=[task_params])
    
    def get_execution_status(self, task_id: str = None) -> Dict[str, Any]:
        """実行状況を取得"""
        
        if task_id:
            # 特定タスクの状況
            if task_id in self.executions:
                execution = self.executions[task_id]
                return {
                    'task_id': task_id,
                    'status': execution.status.value,
                    'start_time': execution.start_time.isoformat() if execution.start_time else None,
                    'end_time': execution.end_time.isoformat() if execution.end_time else None,
                    'result': execution.result,
                    'error': execution.error,
                    'retry_count': execution.retry_count
                }
            else:
                return {'error': 'Task not found'}
        else:
            # 全体の状況
            return {
                'total_executions': len(self.executions),
                'running_tasks': len([e for e in self.executions.values() if e.status == ExecutionStatus.RUNNING]),
                'completed_tasks': len([e for e in self.executions.values() if e.status == ExecutionStatus.SUCCESS]),
                'failed_tasks': len([e for e in self.executions.values() if e.status == ExecutionStatus.FAILURE]),
                'parallel_groups': len(self.parallel_groups),
                'statistics': self.execution_stats
            }
    
    def cancel_execution(self, task_id: str = None, group_id: str = None) -> Dict[str, Any]:
        """実行をキャンセル"""
        
        try:
            if task_id and task_id in self.executions:
                # 単一タスクのキャンセル
                execution = self.executions[task_id]
                
                if execution.celery_task_id:
                    self.celery_app.control.revoke(execution.celery_task_id, terminate=True)
                
                execution.status = ExecutionStatus.REVOKED
                execution.end_time = datetime.utcnow()
                
                return {'status': 'cancelled', 'task_id': task_id}
                
            elif group_id and group_id in self.parallel_groups:
                # 並列グループのキャンセル
                parallel_group = self.parallel_groups[group_id]
                
                if parallel_group.celery_group_id:
                    self.celery_app.control.revoke(parallel_group.celery_group_id, terminate=True)
                
                # グループ内の全タスクをキャンセル
                for task_id in parallel_group.task_ids:
                    if task_id in self.executions:
                        self.executions[task_id].status = ExecutionStatus.REVOKED
                        self.executions[task_id].end_time = datetime.utcnow()
                
                parallel_group.status = ExecutionStatus.REVOKED
                parallel_group.end_time = datetime.utcnow()
                
                return {'status': 'cancelled', 'group_id': group_id}
            else:
                return {'error': 'Task or group not found'}
                
        except Exception as e:
            logger.error(f"Cancellation failed: {e}")
            return {'error': str(e)}
    
    def retry_failed_task(self, task_id: str) -> Dict[str, Any]:
        """失敗したタスクを再試行"""
        
        try:
            if task_id not in self.executions:
                return {'error': 'Task not found'}
            
            execution = self.executions[task_id]
            
            if execution.status != ExecutionStatus.FAILURE:
                return {'error': 'Task is not in failed state'}
            
            if execution.retry_count >= execution.max_retries:
                return {'error': 'Maximum retries exceeded'}
            
            # 再試行
            execution.retry_count += 1
            execution.status = ExecutionStatus.RETRY
            execution.start_time = datetime.utcnow()
            execution.end_time = None
            execution.error = None
            
            # 新しいCeleryタスクを作成（元のタスクノードが必要）
            # 実際の実装では、タスクノードを保存しておく必要がある
            
            logger.info(f"Retrying task {task_id} (attempt {execution.retry_count})")
            
            return {
                'status': 'retrying',
                'task_id': task_id,
                'retry_count': execution.retry_count
            }
            
        except Exception as e:
            logger.error(f"Retry failed for task {task_id}: {e}")
            return {'error': str(e)}
    
    def _update_execution_stats(
        self, 
        results: Dict[str, Any], 
        execution_time: float,
        parallel_analysis: Dict[str, Any]
    ):
        """実行統計を更新"""
        
        self.execution_stats['total_tasks'] += len(results)
        self.execution_stats['completed_tasks'] += len([r for r in results.values() if r.get('status') == 'success'])
        self.execution_stats['failed_tasks'] += len([r for r in results.values() if r.get('status') == 'failure'])
        self.execution_stats['parallel_groups_executed'] += len(parallel_analysis['parallel_groups'])
        
        # 時間節約の計算
        sequential_time = sum(
            group['estimated_time'] for group in parallel_analysis['parallel_groups']
        )
        time_saved = sequential_time - execution_time
        self.execution_stats['total_time_saved'] += max(0, time_saved)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """パフォーマンスメトリクスを取得"""
        
        total_tasks = self.execution_stats['total_tasks']
        if total_tasks == 0:
            return {'message': 'No tasks executed yet'}
        
        success_rate = self.execution_stats['completed_tasks'] / total_tasks
        failure_rate = self.execution_stats['failed_tasks'] / total_tasks
        
        # 平均実行時間の計算
        completed_executions = [e for e in self.executions.values() if e.status == ExecutionStatus.SUCCESS]
        avg_execution_time = 0
        if completed_executions:
            total_time = sum(
                (e.end_time - e.start_time).total_seconds() 
                for e in completed_executions 
                if e.end_time and e.start_time
            )
            avg_execution_time = total_time / len(completed_executions)
        
        return {
            'total_tasks_executed': total_tasks,
            'success_rate': success_rate,
            'failure_rate': failure_rate,
            'average_execution_time': avg_execution_time,
            'total_time_saved': self.execution_stats['total_time_saved'],
            'parallel_groups_executed': self.execution_stats['parallel_groups_executed'],
            'current_active_tasks': len([e for e in self.executions.values() if e.status == ExecutionStatus.RUNNING]),
            'retry_statistics': {
                'tasks_retried': len([e for e in self.executions.values() if e.retry_count > 0]),
                'average_retries': sum(e.retry_count for e in self.executions.values()) / total_tasks if total_tasks > 0 else 0
            }
        }

