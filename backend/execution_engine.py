"""
AIエージェント - 実行エンジン

このモジュールは、計画されたタスクを実行し、進捗を追跡する
実行エンジンを実装します。
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json
import traceback

from task_planner import TaskNode, TaskStatus, DependencyGraph
from tools.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class ExecutionContext:
    """実行コンテキスト"""
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.variables: Dict[str, Any] = {}
        self.execution_log: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
    
    def set_variable(self, key: str, value: Any):
        """変数を設定"""
        self.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """変数を取得"""
        return self.variables.get(key, default)
    
    def log_event(self, event_type: str, message: str, data: Dict[str, Any] = None):
        """イベントをログに記録"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'message': message,
            'data': data or {}
        }
        self.execution_log.append(log_entry)
        logger.info(f"[{self.session_id}] {event_type}: {message}")

class ProgressTracker:
    """実行状況をリアルタイムで追跡"""
    
    def __init__(self):
        self.callbacks: List[Callable] = []
        self.current_execution: Optional[str] = None
        self.execution_stats: Dict[str, Any] = {}
    
    def add_callback(self, callback: Callable):
        """進捗更新のコールバックを追加"""
        self.callbacks.append(callback)
    
    def update_progress(self, session_id: str, task_id: str, status: str, progress: float, message: str = ""):
        """進捗を更新"""
        update_data = {
            'session_id': session_id,
            'task_id': task_id,
            'status': status,
            'progress': progress,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        # 統計情報を更新
        if session_id not in self.execution_stats:
            self.execution_stats[session_id] = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0,
                'start_time': datetime.now().isoformat()
            }
        
        # コールバックを実行
        for callback in self.callbacks:
            try:
                callback(update_data)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def get_execution_stats(self, session_id: str) -> Dict[str, Any]:
        """実行統計を取得"""
        return self.execution_stats.get(session_id, {})

class ErrorHandler:
    """エラーの分類と対処法の決定"""
    
    def __init__(self):
        self.error_patterns = {
            'network_error': ['connection', 'timeout', 'network'],
            'permission_error': ['permission', 'access', 'forbidden'],
            'resource_error': ['memory', 'disk', 'resource'],
            'validation_error': ['invalid', 'validation', 'format']
        }
        self.retry_strategies = {
            'network_error': {'max_retries': 3, 'delay': 5},
            'permission_error': {'max_retries': 1, 'delay': 0},
            'resource_error': {'max_retries': 2, 'delay': 10},
            'validation_error': {'max_retries': 0, 'delay': 0}
        }
    
    def classify_error(self, error_message: str) -> str:
        """エラーを分類"""
        error_message_lower = error_message.lower()
        
        for error_type, patterns in self.error_patterns.items():
            if any(pattern in error_message_lower for pattern in patterns):
                return error_type
        
        return 'unknown_error'
    
    def should_retry(self, task: TaskNode, error_type: str) -> bool:
        """再試行すべきかどうかを判定"""
        strategy = self.retry_strategies.get(error_type, {'max_retries': 0})
        return task.retry_count < strategy['max_retries']
    
    def get_retry_delay(self, error_type: str) -> int:
        """再試行までの遅延時間を取得"""
        strategy = self.retry_strategies.get(error_type, {'delay': 0})
        return strategy['delay']
    
    def suggest_fallback(self, task: TaskNode, error_type: str) -> Optional[Dict[str, Any]]:
        """代替手段を提案"""
        fallback_strategies = {
            'network_error': {
                'tool_name': 'offline_processor',
                'message': 'ネットワークエラーのため、オフライン処理に切り替えます'
            },
            'permission_error': {
                'tool_name': 'alternative_tool',
                'message': '権限エラーのため、代替ツールを使用します'
            }
        }
        
        return fallback_strategies.get(error_type)

class TaskExecutor:
    """個別のタスクを実行"""
    
    def __init__(self, tool_manager: ToolManager, error_handler: ErrorHandler):
        self.tool_manager = tool_manager
        self.error_handler = error_handler
    
    async def execute_task(self, task: TaskNode, context: ExecutionContext) -> Dict[str, Any]:
        """タスクを実行"""
        context.log_event('task_start', f"タスク開始: {task.title}", {'task_id': task.id})
        
        try:
            # パラメータの変数展開
            resolved_parameters = self._resolve_parameters(task.parameters, context)
            
            # ツールを実行
            result = await self.tool_manager.execute_tool(
                task.tool_name, 
                resolved_parameters
            )
            
            # 結果を変数として保存
            context.set_variable(f"{task.id}.result", result)
            
            context.log_event('task_complete', f"タスク完了: {task.title}", {
                'task_id': task.id,
                'result': result
            })
            
            return result
            
        except Exception as e:
            error_message = str(e)
            error_type = self.error_handler.classify_error(error_message)
            
            context.log_event('task_error', f"タスクエラー: {task.title}", {
                'task_id': task.id,
                'error': error_message,
                'error_type': error_type,
                'traceback': traceback.format_exc()
            })
            
            raise e
    
    def _resolve_parameters(self, parameters: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """パラメータ内の変数参照を解決"""
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                # 変数参照を解決
                var_name = value[2:-2].strip()
                resolved[key] = context.get_variable(var_name, value)
            else:
                resolved[key] = value
        
        return resolved

class ExecutionEngine:
    """タスクの実行を管理"""
    
    def __init__(self, tool_manager: ToolManager):
        self.tool_manager = tool_manager
        self.error_handler = ErrorHandler()
        self.task_executor = TaskExecutor(tool_manager, self.error_handler)
        self.progress_tracker = ProgressTracker()
        self.active_executions: Dict[str, asyncio.Task] = {}
    
    async def execute_plan(self, plan: DependencyGraph, session_id: str, user_id: str) -> Dict[str, Any]:
        """実行計画を実行"""
        context = ExecutionContext(session_id, user_id)
        context.log_event('execution_start', "実行計画開始", {
            'total_tasks': len(plan.nodes),
            'session_id': session_id
        })
        
        try:
            # 実行ループ
            while True:
                ready_tasks = plan.get_ready_tasks()
                
                if not ready_tasks:
                    # 実行可能なタスクがない場合、全て完了したかチェック
                    pending_tasks = [t for t in plan.nodes.values() if t.status == TaskStatus.PENDING]
                    if not pending_tasks:
                        break  # 全タスク完了
                    else:
                        # デッドロック状態
                        context.log_event('execution_deadlock', "デッドロック検出", {
                            'pending_tasks': [t.id for t in pending_tasks]
                        })
                        break
                
                # 並列実行
                tasks_to_execute = ready_tasks[:3]  # 最大3つまで並列実行
                execution_tasks = []
                
                for task in tasks_to_execute:
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    
                    # 進捗更新
                    self.progress_tracker.update_progress(
                        session_id, task.id, 'running', 0.0, f"タスク開始: {task.title}"
                    )
                    
                    # 非同期実行
                    execution_task = asyncio.create_task(
                        self._execute_task_with_retry(task, context, session_id)
                    )
                    execution_tasks.append((task, execution_task))
                
                # 実行完了を待機
                for task, execution_task in execution_tasks:
                    try:
                        result = await execution_task
                        plan.mark_completed(task.id, result)
                        
                        self.progress_tracker.update_progress(
                            session_id, task.id, 'completed', 1.0, f"タスク完了: {task.title}"
                        )
                        
                    except Exception as e:
                        plan.mark_failed(task.id, str(e))
                        
                        self.progress_tracker.update_progress(
                            session_id, task.id, 'failed', 0.0, f"タスク失敗: {str(e)}"
                        )
                        
                        # 失敗したタスクに依存するタスクもキャンセル
                        self._cancel_dependent_tasks(plan, task.id)
            
            # 実行結果をまとめる
            execution_result = {
                'session_id': session_id,
                'status': 'completed',
                'execution_log': context.execution_log,
                'task_status': plan.get_task_status(),
                'execution_time': (datetime.now() - context.start_time).total_seconds()
            }
            
            context.log_event('execution_complete', "実行計画完了", execution_result)
            
            return execution_result
            
        except Exception as e:
            context.log_event('execution_error', f"実行エラー: {str(e)}", {
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            
            return {
                'session_id': session_id,
                'status': 'failed',
                'error': str(e),
                'execution_log': context.execution_log,
                'task_status': plan.get_task_status()
            }
    
    async def _execute_task_with_retry(self, task: TaskNode, context: ExecutionContext, session_id: str) -> Dict[str, Any]:
        """再試行機能付きでタスクを実行"""
        last_error = None
        
        while task.retry_count <= task.max_retries:
            try:
                result = await self.task_executor.execute_task(task, context)
                return result
                
            except Exception as e:
                last_error = e
                error_type = self.error_handler.classify_error(str(e))
                
                if self.error_handler.should_retry(task, error_type):
                    task.retry_count += 1
                    delay = self.error_handler.get_retry_delay(error_type)
                    
                    context.log_event('task_retry', f"タスク再試行: {task.title}", {
                        'task_id': task.id,
                        'retry_count': task.retry_count,
                        'delay': delay,
                        'error_type': error_type
                    })
                    
                    self.progress_tracker.update_progress(
                        session_id, task.id, 'retrying', 0.0, 
                        f"再試行中 ({task.retry_count}/{task.max_retries})"
                    )
                    
                    if delay > 0:
                        await asyncio.sleep(delay)
                else:
                    break
        
        # 再試行回数を超えた場合
        raise last_error
    
    def _cancel_dependent_tasks(self, plan: DependencyGraph, failed_task_id: str):
        """失敗したタスクに依存するタスクをキャンセル"""
        def cancel_recursive(task_id: str):
            if task_id in plan.edges:
                for dependent_id in plan.edges[task_id]:
                    if dependent_id in plan.nodes:
                        dependent_task = plan.nodes[dependent_id]
                        if dependent_task.status == TaskStatus.PENDING:
                            dependent_task.status = TaskStatus.CANCELLED
                            cancel_recursive(dependent_id)
        
        cancel_recursive(failed_task_id)
    
    def add_progress_callback(self, callback: Callable):
        """進捗更新のコールバックを追加"""
        self.progress_tracker.add_callback(callback)
    
    def get_execution_status(self, session_id: str) -> Dict[str, Any]:
        """実行状況を取得"""
        return self.progress_tracker.get_execution_stats(session_id)
    
    async def cancel_execution(self, session_id: str):
        """実行をキャンセル"""
        if session_id in self.active_executions:
            task = self.active_executions[session_id]
            task.cancel()
            del self.active_executions[session_id]

