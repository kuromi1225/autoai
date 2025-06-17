"""
Task Manager - タスク管理システム

このモジュールは、AIエージェントのタスク実行を管理します。
タスクの作成、実行、進捗追跡、結果管理を行います。
"""

import uuid
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """タスクステータス"""
    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """ステップステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TaskStep:
    """タスクステップ"""
    id: int
    title: str
    description: str
    type: str
    estimated_time: int
    dependencies: List[int]
    tools: List[str]
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@dataclass
class Task:
    """タスク"""
    id: str
    description: str
    requirements: List[str]
    github_repo: Optional[str]
    status: TaskStatus = TaskStatus.CREATED
    steps: List[TaskStep] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    current_step: Optional[int] = None
    logs: List[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.logs is None:
            self.logs = []
        if self.created_at is None:
            self.created_at = datetime.now()

class TaskManager:
    """
    タスク管理システム
    
    AIエージェントのタスク実行を統合的に管理します。
    """
    
    def __init__(self, qwen_engine, mcp_server):
        """
        タスクマネージャーを初期化
        
        Args:
            qwen_engine: Qwenエンジンインスタンス
            mcp_server: MCPサーバーインスタンス
        """
        self.qwen_engine = qwen_engine
        self.mcp_server = mcp_server
        
        # タスク管理
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        
        # 実行環境
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("Task manager initialized")
    
    def create_task(
        self, 
        description: str, 
        requirements: List[str] = None,
        github_repo: str = None
    ) -> str:
        """
        新しいタスクを作成
        
        Args:
            description: タスクの説明
            requirements: 要件リスト
            github_repo: GitHubリポジトリURL
            
        Returns:
            タスクID
        """
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            description=description,
            requirements=requirements or [],
            github_repo=github_repo
        )
        
        self.tasks[task_id] = task
        
        logger.info(f"Task created: {task_id}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        タスク情報を取得
        
        Args:
            task_id: タスクID
            
        Returns:
            タスク情報
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "description": task.description,
            "requirements": task.requirements,
            "github_repo": task.github_repo,
            "status": task.status.value,
            "progress": task.progress,
            "current_step": task.current_step,
            "steps": [
                {
                    "id": step.id,
                    "title": step.title,
                    "description": step.description,
                    "type": step.type,
                    "status": step.status.value,
                    "estimated_time": step.estimated_time
                }
                for step in task.steps
            ],
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "logs": task.logs[-50:],  # 最新50件のログ
            "result": task.result,
            "error": task.error
        }
    
    def start_task(self, task_id: str) -> bool:
        """
        タスクを開始
        
        Args:
            task_id: タスクID
            
        Returns:
            開始成功フラグ
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False
        
        if task.status != TaskStatus.CREATED:
            logger.error(f"Task cannot be started: {task_id} (status: {task.status})")
            return False
        
        # タスクを別スレッドで実行
        thread = threading.Thread(target=self._execute_task, args=(task_id,))
        thread.daemon = True
        thread.start()
        
        self.running_tasks[task_id] = thread
        
        logger.info(f"Task started: {task_id}")
        return True
    
    def stop_task(self, task_id: str) -> bool:
        """
        タスクを停止
        
        Args:
            task_id: タスクID
            
        Returns:
            停止成功フラグ
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return True
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        # 実行中のスレッドがあれば停止を試行
        if task_id in self.running_tasks:
            # 注意: Pythonスレッドは強制終了できないため、
            # タスク内でステータスをチェックして自然終了させる
            pass
        
        logger.info(f"Task stopped: {task_id}")
        return True
    
    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """
        タスクの進捗を取得
        
        Args:
            task_id: タスクID
            
        Returns:
            進捗情報
        """
        task = self.tasks.get(task_id)
        if not task:
            return {}
        
        return {
            "task_id": task_id,
            "status": task.status.value,
            "progress": task.progress,
            "current_step": task.current_step,
            "logs": task.logs[-10:],  # 最新10件のログ
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_task(self, task_id: str):
        """
        タスクを実行（内部メソッド）
        
        Args:
            task_id: タスクID
        """
        task = self.tasks[task_id]
        
        try:
            # タスク開始
            task.status = TaskStatus.PLANNING
            task.started_at = datetime.now()
            self._log_task(task_id, "タスクを開始しました")
            
            # ステップ1: タスク分解
            self._log_task(task_id, "タスクを分解しています...")
            steps_data = self.qwen_engine.decompose_task(task.description)
            
            if not steps_data:
                raise Exception("タスクの分解に失敗しました")
            
            # ステップオブジェクトを作成
            task.steps = []
            for step_data in steps_data:
                step = TaskStep(
                    id=step_data.get('id', len(task.steps) + 1),
                    title=step_data.get('title', ''),
                    description=step_data.get('description', ''),
                    type=step_data.get('type', 'code'),
                    estimated_time=int(step_data.get('estimated_time', 10)),
                    dependencies=step_data.get('dependencies', []),
                    tools=step_data.get('tools', [])
                )
                task.steps.append(step)
            
            self._log_task(task_id, f"{len(task.steps)}個のステップに分解しました")
            
            # ステップ2: ステップ実行
            task.status = TaskStatus.EXECUTING
            
            for i, step in enumerate(task.steps):
                if task.status == TaskStatus.CANCELLED:
                    break
                
                task.current_step = step.id
                self._execute_step(task_id, step)
                
                # 進捗更新
                task.progress = (i + 1) / len(task.steps)
            
            # タスク完了
            if task.status != TaskStatus.CANCELLED:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                self._log_task(task_id, "タスクが完了しました")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self._log_task(task_id, f"タスクが失敗しました: {e}")
            logger.error(f"Task execution failed: {task_id} - {e}")
        
        finally:
            # 実行中タスクリストから削除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def _execute_step(self, task_id: str, step: TaskStep):
        """
        ステップを実行
        
        Args:
            task_id: タスクID
            step: 実行するステップ
        """
        try:
            step.status = StepStatus.RUNNING
            step.start_time = datetime.now()
            
            self._log_task(task_id, f"ステップ実行中: {step.title}")
            
            # ステップタイプに応じた実行
            if step.type == "code":
                result = self._execute_code_step(task_id, step)
            elif step.type == "research":
                result = self._execute_research_step(task_id, step)
            elif step.type == "planning":
                result = self._execute_planning_step(task_id, step)
            elif step.type == "testing":
                result = self._execute_testing_step(task_id, step)
            elif step.type == "documentation":
                result = self._execute_documentation_step(task_id, step)
            else:
                result = self._execute_generic_step(task_id, step)
            
            step.result = result
            step.status = StepStatus.COMPLETED
            step.end_time = datetime.now()
            
            self._log_task(task_id, f"ステップ完了: {step.title}")
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.end_time = datetime.now()
            
            self._log_task(task_id, f"ステップ失敗: {step.title} - {e}")
            
            # エラー解決を試行
            self._try_resolve_error(task_id, step, str(e))
    
    def _execute_code_step(self, task_id: str, step: TaskStep) -> Dict[str, Any]:
        """コードステップを実行"""
        # コード生成
        code = self.qwen_engine.generate_code(
            requirements=step.description,
            language="python"
        )
        
        if not code:
            raise Exception("コード生成に失敗しました")
        
        # ファイルに保存
        filename = f"step_{step.id}.py"
        
        # MCPサーバーを使用してファイル保存
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        save_result = loop.run_until_complete(
            self.mcp_server.handle_request({
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "file_write",
                    "arguments": {
                        "path": filename,
                        "content": code
                    }
                }
            })
        )
        
        loop.close()
        
        return {
            "code": code,
            "filename": filename,
            "save_result": save_result
        }
    
    def _execute_research_step(self, task_id: str, step: TaskStep) -> Dict[str, Any]:
        """リサーチステップを実行"""
        # 研究内容を生成
        research_prompt = f"""
以下のトピックについて調査してください：
{step.description}

調査結果をまとめて報告してください。
"""
        
        research_result = self.qwen_engine.generate_text(research_prompt)
        
        return {
            "research_result": research_result,
            "topic": step.description
        }
    
    def _execute_planning_step(self, task_id: str, step: TaskStep) -> Dict[str, Any]:
        """プランニングステップを実行"""
        planning_prompt = f"""
以下の計画を立ててください：
{step.description}

詳細な計画を作成してください。
"""
        
        plan = self.qwen_engine.generate_text(planning_prompt)
        
        return {
            "plan": plan,
            "description": step.description
        }
    
    def _execute_testing_step(self, task_id: str, step: TaskStep) -> Dict[str, Any]:
        """テストステップを実行"""
        # MCPサーバーを使用してテスト実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        test_result = loop.run_until_complete(
            self.mcp_server.handle_request({
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "run_tests",
                    "arguments": {
                        "test_path": step.description
                    }
                }
            })
        )
        
        loop.close()
        
        return test_result
    
    def _execute_documentation_step(self, task_id: str, step: TaskStep) -> Dict[str, Any]:
        """ドキュメンテーションステップを実行"""
        doc_prompt = f"""
以下についてドキュメントを作成してください：
{step.description}

Markdown形式で詳細なドキュメントを作成してください。
"""
        
        documentation = self.qwen_engine.generate_text(doc_prompt)
        
        # ファイルに保存
        filename = f"documentation_step_{step.id}.md"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        save_result = loop.run_until_complete(
            self.mcp_server.handle_request({
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "file_write",
                    "arguments": {
                        "path": filename,
                        "content": documentation
                    }
                }
            })
        )
        
        loop.close()
        
        return {
            "documentation": documentation,
            "filename": filename,
            "save_result": save_result
        }
    
    def _execute_generic_step(self, task_id: str, step: TaskStep) -> Dict[str, Any]:
        """汎用ステップを実行"""
        result = self.qwen_engine.generate_text(
            f"以下のタスクを実行してください：\n{step.description}"
        )
        
        return {
            "result": result,
            "description": step.description
        }
    
    def _try_resolve_error(self, task_id: str, step: TaskStep, error_message: str):
        """エラー解決を試行"""
        try:
            self._log_task(task_id, f"エラー解決を試行中: {error_message}")
            
            # エラー分析
            error_analysis = self.qwen_engine.analyze_error(
                error_message=error_message,
                code=step.result.get('code', '') if step.result else '',
                context=step.description
            )
            
            if error_analysis and error_analysis.get('solutions'):
                solution = error_analysis['solutions'][0]
                self._log_task(task_id, f"解決策を発見: {solution.get('description', '')}")
                
                # 解決策を適用（簡単な場合のみ）
                if solution.get('code_fix'):
                    step.result = step.result or {}
                    step.result['fixed_code'] = solution['code_fix']
                    step.status = StepStatus.COMPLETED
                    self._log_task(task_id, "エラーを自動修正しました")
            
        except Exception as e:
            self._log_task(task_id, f"エラー解決に失敗: {e}")
    
    def _log_task(self, task_id: str, message: str):
        """タスクログを記録"""
        task = self.tasks.get(task_id)
        if task:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            task.logs.append(log_entry)
            logger.info(f"Task {task_id}: {message}")
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """全タスクの一覧を取得"""
        return [self.get_task(task_id) for task_id in self.tasks.keys()]
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """完了したタスクをクリーンアップ"""
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                and task.completed_at 
                and (current_time - task.completed_at).total_seconds() > max_age_hours * 3600):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            logger.info(f"Cleaned up old task: {task_id}")
        
        return len(tasks_to_remove)

