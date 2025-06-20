"""
AIエージェント - タスク計画システム

このモジュールは、ユーザーの要求を分析し、実行可能なタスクに分解する
タスク計画システムを実装します。
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """タスクの実行状態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """タスクの優先度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TaskNode:
    """個別のタスクを表現するデータ構造"""
    id: str
    title: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str]  # 依存するタスクのID
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskNode':
        """辞書から復元"""
        data['status'] = TaskStatus(data['status'])
        data['priority'] = TaskPriority(data['priority'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)

class DependencyGraph:
    """タスク間の依存関係を管理"""
    
    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}
        self.edges: Dict[str, List[str]] = {}  # task_id -> [dependent_task_ids]
    
    def add_task(self, task: TaskNode):
        """タスクを追加"""
        self.nodes[task.id] = task
        if task.id not in self.edges:
            self.edges[task.id] = []
        
        # 依存関係を設定
        for dep_id in task.dependencies:
            if dep_id in self.edges:
                self.edges[dep_id].append(task.id)
            else:
                self.edges[dep_id] = [task.id]
    
    def get_ready_tasks(self) -> List[TaskNode]:
        """実行可能なタスクを取得（依存関係が満たされているタスク）"""
        ready_tasks = []
        
        for task_id, task in self.nodes.items():
            if task.status != TaskStatus.PENDING:
                continue
            
            # 全ての依存タスクが完了しているかチェック
            all_deps_completed = True
            for dep_id in task.dependencies:
                if dep_id in self.nodes:
                    if self.nodes[dep_id].status != TaskStatus.COMPLETED:
                        all_deps_completed = False
                        break
                else:
                    # 依存タスクが存在しない場合はエラー
                    all_deps_completed = False
                    break
            
            if all_deps_completed:
                ready_tasks.append(task)
        
        # 優先度順にソート
        ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)
        return ready_tasks
    
    def mark_completed(self, task_id: str, result: Dict[str, Any] = None):
        """タスクを完了としてマーク"""
        if task_id in self.nodes:
            self.nodes[task_id].status = TaskStatus.COMPLETED
            self.nodes[task_id].completed_at = datetime.now()
            self.nodes[task_id].result = result
    
    def mark_failed(self, task_id: str, error: str):
        """タスクを失敗としてマーク"""
        if task_id in self.nodes:
            self.nodes[task_id].status = TaskStatus.FAILED
            self.nodes[task_id].error = error
            self.nodes[task_id].completed_at = datetime.now()
    
    def get_task_status(self) -> Dict[str, Any]:
        """全タスクの状態を取得"""
        status_counts = {status.value: 0 for status in TaskStatus}
        for task in self.nodes.values():
            status_counts[task.status.value] += 1
        
        return {
            'total_tasks': len(self.nodes),
            'status_counts': status_counts,
            'tasks': [task.to_dict() for task in self.nodes.values()]
        }

class TaskPlanner:
    """ユーザーの要求を分析し、実行可能なタスクに分解"""
    
    def __init__(self):
        self.available_tools = {}
        self.planning_strategies = {}
    
    def register_tool(self, tool_name: str, tool_info: Dict[str, Any]):
        """利用可能なツールを登録"""
        self.available_tools[tool_name] = tool_info
    
    def analyze_request(self, user_request: str) -> Dict[str, Any]:
        """ユーザーの要求を分析"""
        # TODO: LLMを使用してより高度な分析を実装
        analysis = {
            'intent': self._extract_intent(user_request),
            'entities': self._extract_entities(user_request),
            'complexity': self._assess_complexity(user_request),
            'required_tools': self._identify_required_tools(user_request)
        }
        return analysis
    
    def create_execution_plan(self, user_request: str) -> DependencyGraph:
        """実行計画を作成"""
        analysis = self.analyze_request(user_request)
        graph = DependencyGraph()
        
        # 基本的な計画作成ロジック
        tasks = self._generate_tasks(analysis, user_request)
        
        for task in tasks:
            graph.add_task(task)
        
        return graph
    
    def _extract_intent(self, request: str) -> str:
        """意図を抽出"""
        # 簡単なキーワードベースの分析
        if any(word in request.lower() for word in ['作成', 'create', '生成', 'generate']):
            return 'create'
        elif any(word in request.lower() for word in ['分析', 'analyze', '解析']):
            return 'analyze'
        elif any(word in request.lower() for word in ['検索', 'search', '探す']):
            return 'search'
        elif any(word in request.lower() for word in ['修正', 'fix', '直す']):
            return 'fix'
        else:
            return 'general'
    
    def _extract_entities(self, request: str) -> List[str]:
        """エンティティを抽出"""
        # TODO: より高度なNER実装
        entities = []
        if 'ファイル' in request or 'file' in request.lower():
            entities.append('file')
        if 'ウェブサイト' in request or 'website' in request.lower():
            entities.append('website')
        if 'データ' in request or 'data' in request.lower():
            entities.append('data')
        return entities
    
    def _assess_complexity(self, request: str) -> str:
        """複雑さを評価"""
        word_count = len(request.split())
        if word_count < 10:
            return 'simple'
        elif word_count < 30:
            return 'medium'
        else:
            return 'complex'
    
    def _identify_required_tools(self, request: str) -> List[str]:
        """必要なツールを特定"""
        required_tools = []
        
        # キーワードベースでツールを特定
        if any(word in request.lower() for word in ['ブラウザ', 'browser', 'web', 'サイト']):
            required_tools.append('browser')
        if any(word in request.lower() for word in ['ファイル', 'file', '編集']):
            required_tools.append('file_editor')
        if any(word in request.lower() for word in ['コード', 'code', 'プログラム']):
            required_tools.append('code_executor')
        if any(word in request.lower() for word in ['画像', 'image', '写真']):
            required_tools.append('image_generator')
        
        return required_tools
    
    def _generate_tasks(self, analysis: Dict[str, Any], request: str) -> List[TaskNode]:
        """タスクを生成"""
        tasks = []
        intent = analysis['intent']
        required_tools = analysis['required_tools']
        
        if intent == 'create' and 'website' in analysis['entities']:
            # ウェブサイト作成のタスク分解例
            tasks.extend(self._create_website_tasks(request))
        elif intent == 'analyze' and 'data' in analysis['entities']:
            # データ分析のタスク分解例
            tasks.extend(self._create_data_analysis_tasks(request))
        else:
            # 汎用的なタスク作成
            tasks.extend(self._create_generic_tasks(request, required_tools))
        
        return tasks
    
    def _create_website_tasks(self, request: str) -> List[TaskNode]:
        """ウェブサイト作成タスクを生成"""
        tasks = []
        
        # 1. 要件分析
        task1 = TaskNode(
            id=str(uuid.uuid4()),
            title="要件分析",
            description="ウェブサイトの要件を分析する",
            tool_name="text_analyzer",
            parameters={"text": request},
            dependencies=[]
        )
        tasks.append(task1)
        
        # 2. デザイン作成
        task2 = TaskNode(
            id=str(uuid.uuid4()),
            title="デザイン作成",
            description="ウェブサイトのデザインを作成する",
            tool_name="design_generator",
            parameters={"requirements": "{{" + task1.id + ".result}}"},
            dependencies=[task1.id]
        )
        tasks.append(task2)
        
        # 3. HTML/CSS作成
        task3 = TaskNode(
            id=str(uuid.uuid4()),
            title="HTML/CSS作成",
            description="HTMLとCSSファイルを作成する",
            tool_name="code_generator",
            parameters={"design": "{{" + task2.id + ".result}}"},
            dependencies=[task2.id]
        )
        tasks.append(task3)
        
        return tasks
    
    def _create_data_analysis_tasks(self, request: str) -> List[TaskNode]:
        """データ分析タスクを生成"""
        tasks = []
        
        # 1. データ読み込み
        task1 = TaskNode(
            id=str(uuid.uuid4()),
            title="データ読み込み",
            description="分析対象のデータを読み込む",
            tool_name="data_loader",
            parameters={"source": request},
            dependencies=[]
        )
        tasks.append(task1)
        
        # 2. データ前処理
        task2 = TaskNode(
            id=str(uuid.uuid4()),
            title="データ前処理",
            description="データをクリーニングし前処理を行う",
            tool_name="data_preprocessor",
            parameters={"data": "{{" + task1.id + ".result}}"},
            dependencies=[task1.id]
        )
        tasks.append(task2)
        
        # 3. 分析実行
        task3 = TaskNode(
            id=str(uuid.uuid4()),
            title="分析実行",
            description="データ分析を実行する",
            tool_name="data_analyzer",
            parameters={"data": "{{" + task2.id + ".result}}"},
            dependencies=[task2.id]
        )
        tasks.append(task3)
        
        return tasks
    
    def _create_generic_tasks(self, request: str, required_tools: List[str]) -> List[TaskNode]:
        """汎用的なタスクを生成"""
        tasks = []
        
        # 基本的なタスク作成
        task = TaskNode(
            id=str(uuid.uuid4()),
            title="要求処理",
            description=f"ユーザーの要求を処理: {request}",
            tool_name=required_tools[0] if required_tools else "text_processor",
            parameters={"request": request},
            dependencies=[]
        )
        tasks.append(task)
        
        return tasks

