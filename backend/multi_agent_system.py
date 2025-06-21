"""
マルチエージェントシステム

PM（プロジェクトマネージャー）、PG（プログラマー）、QA（品質保証）、テスター
の役割を持つAIエージェントが協調して開発タスクを実行
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentRole(Enum):
    """エージェントの役割"""
    PROJECT_MANAGER = "pm"
    PROGRAMMER = "pg"
    QA_ENGINEER = "qa"
    TESTER = "tester"
    ARCHITECT = "architect"
    DEVOPS = "devops"

class TaskStatus(Enum):
    """タスクステータス"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

class TaskPriority(Enum):
    """タスク優先度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Task:
    """タスク定義"""
    id: str
    title: str
    description: str
    role: AgentRole
    priority: TaskPriority
    status: TaskStatus
    created_at: str
    updated_at: str
    assigned_agent: Optional[str] = None
    dependencies: List[str] = None
    estimated_time: Optional[int] = None  # 分
    actual_time: Optional[int] = None
    deliverables: List[str] = None
    feedback: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.deliverables is None:
            self.deliverables = []
        if self.feedback is None:
            self.feedback = []

@dataclass
class AgentMessage:
    """エージェント間メッセージ"""
    id: str
    from_agent: str
    to_agent: str
    message_type: str
    content: Dict[str, Any]
    timestamp: str
    task_id: Optional[str] = None

class BaseAgent(ABC):
    """基底エージェントクラス"""
    
    def __init__(self, agent_id: str, role: AgentRole, qwq_engine):
        self.agent_id = agent_id
        self.role = role
        self.qwq_engine = qwq_engine
        self.is_active = True
        self.current_task = None
        self.message_queue = asyncio.Queue()
        self.capabilities = []
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_completion_time": 0.0,
            "quality_score": 0.0
        }
        
        # 役割固有の初期化
        self._initialize_role_specific()
    
    @abstractmethod
    def _initialize_role_specific(self):
        """役割固有の初期化"""
        pass
    
    @abstractmethod
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """タスクを処理"""
        pass
    
    async def send_message(self, to_agent: str, message_type: str, 
                          content: Dict[str, Any], task_id: Optional[str] = None):
        """他のエージェントにメッセージを送信"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat(),
            task_id=task_id
        )
        
        # メッセージをマルチエージェントシステムに送信
        await self._send_to_system(message)
    
    async def receive_message(self, message: AgentMessage):
        """メッセージを受信"""
        await self.message_queue.put(message)
    
    async def _send_to_system(self, message: AgentMessage):
        """システムにメッセージを送信（実装は子クラスで）"""
        pass
    
    async def generate_response(self, prompt: str, context: Optional[Dict] = None) -> str:
        """QwQ-32Bを使用してレスポンスを生成"""
        try:
            # コンテキストを含むプロンプトを構築
            full_prompt = self._build_prompt(prompt, context)
            
            # QwQ-32Bで推論
            response = await self.qwq_engine.generate_response_async(
                full_prompt,
                max_length=1024,
                temperature=0.7
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response for {self.agent_id}: {e}")
            return f"Error: {str(e)}"
    
    def _build_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
        """役割に応じたプロンプトを構築"""
        role_context = self._get_role_context()
        
        full_prompt = f"""You are a {role_context['title']} in a software development team.

Role Description: {role_context['description']}

Responsibilities:
{chr(10).join(f"- {resp}" for resp in role_context['responsibilities'])}

Current Task Context:
{json.dumps(context, indent=2) if context else "No specific context"}

Request: {prompt}

Please provide a detailed and professional response based on your role and expertise."""

        return full_prompt
    
    @abstractmethod
    def _get_role_context(self) -> Dict[str, Any]:
        """役割のコンテキストを取得"""
        pass
    
    def update_performance_metrics(self, task: Task, completion_time: int, quality_score: float):
        """パフォーマンス指標を更新"""
        if task.status == TaskStatus.COMPLETED:
            self.performance_metrics["tasks_completed"] += 1
            
            # 平均完了時間を更新
            total_tasks = self.performance_metrics["tasks_completed"]
            current_avg = self.performance_metrics["average_completion_time"]
            self.performance_metrics["average_completion_time"] = (
                (current_avg * (total_tasks - 1) + completion_time) / total_tasks
            )
            
            # 品質スコアを更新
            self.performance_metrics["quality_score"] = (
                (self.performance_metrics["quality_score"] * (total_tasks - 1) + quality_score) / total_tasks
            )
        else:
            self.performance_metrics["tasks_failed"] += 1

class ProjectManagerAgent(BaseAgent):
    """プロジェクトマネージャーエージェント"""
    
    def _initialize_role_specific(self):
        self.capabilities = [
            "task_decomposition",
            "project_planning",
            "resource_allocation",
            "progress_tracking",
            "risk_management"
        ]
    
    def _get_role_context(self) -> Dict[str, Any]:
        return {
            "title": "Project Manager",
            "description": "Responsible for project planning, task management, and team coordination",
            "responsibilities": [
                "Break down complex requirements into manageable tasks",
                "Assign tasks to appropriate team members",
                "Monitor project progress and timelines",
                "Identify and mitigate risks",
                "Ensure quality standards are met",
                "Coordinate between different team roles"
            ]
        }
    
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """PMタスクを処理"""
        try:
            if "decompose" in task.description.lower():
                return await self._decompose_requirements(task)
            elif "plan" in task.description.lower():
                return await self._create_project_plan(task)
            elif "review" in task.description.lower():
                return await self._review_progress(task)
            else:
                return await self._general_management_task(task)
                
        except Exception as e:
            logger.error(f"PM task processing error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _decompose_requirements(self, task: Task) -> Dict[str, Any]:
        """要件をタスクに分解"""
        prompt = f"""
        Please decompose the following requirement into specific, actionable tasks:
        
        Requirement: {task.description}
        
        For each task, provide:
        1. Task title
        2. Detailed description
        3. Assigned role (PM/PG/QA/Tester)
        4. Estimated time in hours
        5. Dependencies
        6. Acceptance criteria
        
        Format the response as a JSON array of tasks.
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        try:
            # JSONレスポンスをパース
            tasks_data = json.loads(response)
            
            # タスクオブジェクトを作成
            subtasks = []
            for task_data in tasks_data:
                subtask = Task(
                    id=str(uuid.uuid4()),
                    title=task_data.get("title", ""),
                    description=task_data.get("description", ""),
                    role=AgentRole(task_data.get("role", "pg")),
                    priority=TaskPriority.MEDIUM,
                    status=TaskStatus.PENDING,
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    estimated_time=task_data.get("estimated_time", 60),
                    dependencies=task_data.get("dependencies", [])
                )
                subtasks.append(subtask)
            
            return {
                "status": "success",
                "subtasks": [asdict(t) for t in subtasks],
                "total_estimated_time": sum(t.estimated_time or 0 for t in subtasks)
            }
            
        except json.JSONDecodeError:
            # JSONパースに失敗した場合、テキストレスポンスを返す
            return {
                "status": "partial_success",
                "analysis": response,
                "subtasks": []
            }
    
    async def _create_project_plan(self, task: Task) -> Dict[str, Any]:
        """プロジェクト計画を作成"""
        prompt = f"""
        Create a detailed project plan for: {task.description}
        
        Include:
        1. Project phases
        2. Milestones
        3. Resource requirements
        4. Risk assessment
        5. Timeline estimation
        6. Quality gates
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "project_plan": response,
            "created_at": datetime.now().isoformat()
        }
    
    async def _review_progress(self, task: Task) -> Dict[str, Any]:
        """進捗をレビュー"""
        prompt = f"""
        Review the current project progress and provide recommendations:
        
        Current Status: {task.description}
        
        Analyze:
        1. Progress against timeline
        2. Quality metrics
        3. Resource utilization
        4. Risks and issues
        5. Recommendations for improvement
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "progress_review": response,
            "reviewed_at": datetime.now().isoformat()
        }
    
    async def _general_management_task(self, task: Task) -> Dict[str, Any]:
        """一般的な管理タスク"""
        prompt = f"As a project manager, please handle this task: {task.description}"
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "response": response
        }

class ProgrammerAgent(BaseAgent):
    """プログラマーエージェント"""
    
    def _initialize_role_specific(self):
        self.capabilities = [
            "code_development",
            "architecture_design",
            "code_review",
            "debugging",
            "documentation"
        ]
    
    def _get_role_context(self) -> Dict[str, Any]:
        return {
            "title": "Software Developer/Programmer",
            "description": "Responsible for writing, testing, and maintaining code",
            "responsibilities": [
                "Implement features according to specifications",
                "Write clean, maintainable, and efficient code",
                "Conduct code reviews",
                "Debug and fix issues",
                "Create technical documentation",
                "Follow coding standards and best practices"
            ]
        }
    
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """PGタスクを処理"""
        try:
            if "implement" in task.description.lower() or "code" in task.description.lower():
                return await self._implement_feature(task)
            elif "review" in task.description.lower():
                return await self._review_code(task)
            elif "debug" in task.description.lower() or "fix" in task.description.lower():
                return await self._debug_issue(task)
            elif "design" in task.description.lower():
                return await self._design_architecture(task)
            else:
                return await self._general_programming_task(task)
                
        except Exception as e:
            logger.error(f"PG task processing error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _implement_feature(self, task: Task) -> Dict[str, Any]:
        """機能を実装"""
        prompt = f"""
        Implement the following feature:
        
        Feature Description: {task.description}
        
        Please provide:
        1. Code implementation
        2. Comments explaining the logic
        3. Error handling
        4. Unit tests
        5. Documentation
        
        Use best practices and ensure code quality.
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "implementation": response,
            "deliverables": ["source_code", "unit_tests", "documentation"],
            "implemented_at": datetime.now().isoformat()
        }
    
    async def _review_code(self, task: Task) -> Dict[str, Any]:
        """コードをレビュー"""
        prompt = f"""
        Review the following code and provide feedback:
        
        Code to Review: {task.description}
        
        Check for:
        1. Code quality and readability
        2. Performance issues
        3. Security vulnerabilities
        4. Best practices compliance
        5. Potential bugs
        6. Suggestions for improvement
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "code_review": response,
            "reviewed_at": datetime.now().isoformat()
        }
    
    async def _debug_issue(self, task: Task) -> Dict[str, Any]:
        """問題をデバッグ"""
        prompt = f"""
        Debug the following issue:
        
        Issue Description: {task.description}
        
        Provide:
        1. Root cause analysis
        2. Step-by-step debugging approach
        3. Proposed solution
        4. Prevention measures
        5. Test cases to verify the fix
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "debug_analysis": response,
            "debugged_at": datetime.now().isoformat()
        }
    
    async def _design_architecture(self, task: Task) -> Dict[str, Any]:
        """アーキテクチャを設計"""
        prompt = f"""
        Design the architecture for:
        
        Requirements: {task.description}
        
        Include:
        1. System architecture diagram
        2. Component breakdown
        3. Technology stack recommendations
        4. Data flow design
        5. Scalability considerations
        6. Security considerations
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "architecture_design": response,
            "designed_at": datetime.now().isoformat()
        }
    
    async def _general_programming_task(self, task: Task) -> Dict[str, Any]:
        """一般的なプログラミングタスク"""
        prompt = f"As a software developer, please handle this task: {task.description}"
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "response": response
        }

class QAEngineerAgent(BaseAgent):
    """品質保証エンジニアエージェント"""
    
    def _initialize_role_specific(self):
        self.capabilities = [
            "quality_assurance",
            "test_planning",
            "code_review",
            "process_improvement",
            "standards_compliance"
        ]
    
    def _get_role_context(self) -> Dict[str, Any]:
        return {
            "title": "Quality Assurance Engineer",
            "description": "Responsible for ensuring software quality and process compliance",
            "responsibilities": [
                "Define quality standards and processes",
                "Review code for quality and compliance",
                "Create test strategies and plans",
                "Monitor quality metrics",
                "Identify process improvements",
                "Ensure adherence to coding standards"
            ]
        }
    
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """QAタスクを処理"""
        try:
            if "review" in task.description.lower():
                return await self._quality_review(task)
            elif "standard" in task.description.lower():
                return await self._check_standards(task)
            elif "process" in task.description.lower():
                return await self._improve_process(task)
            elif "plan" in task.description.lower():
                return await self._create_qa_plan(task)
            else:
                return await self._general_qa_task(task)
                
        except Exception as e:
            logger.error(f"QA task processing error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _quality_review(self, task: Task) -> Dict[str, Any]:
        """品質レビューを実施"""
        prompt = f"""
        Conduct a comprehensive quality review:
        
        Subject: {task.description}
        
        Evaluate:
        1. Code quality metrics
        2. Adherence to coding standards
        3. Test coverage
        4. Documentation quality
        5. Performance considerations
        6. Security aspects
        7. Maintainability
        
        Provide specific recommendations for improvement.
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "quality_review": response,
            "quality_score": 85,  # 仮の品質スコア
            "reviewed_at": datetime.now().isoformat()
        }
    
    async def _check_standards(self, task: Task) -> Dict[str, Any]:
        """標準準拠をチェック"""
        prompt = f"""
        Check compliance with coding standards and best practices:
        
        Code/Process: {task.description}
        
        Verify:
        1. Coding style compliance
        2. Naming conventions
        3. Documentation standards
        4. Security guidelines
        5. Performance standards
        6. Accessibility requirements
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "standards_check": response,
            "compliance_score": 90,  # 仮の準拠スコア
            "checked_at": datetime.now().isoformat()
        }
    
    async def _improve_process(self, task: Task) -> Dict[str, Any]:
        """プロセス改善を提案"""
        prompt = f"""
        Analyze and suggest improvements for the development process:
        
        Current Process: {task.description}
        
        Provide:
        1. Current process analysis
        2. Identified bottlenecks
        3. Improvement recommendations
        4. Implementation plan
        5. Expected benefits
        6. Risk assessment
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "process_improvement": response,
            "analyzed_at": datetime.now().isoformat()
        }
    
    async def _create_qa_plan(self, task: Task) -> Dict[str, Any]:
        """QA計画を作成"""
        prompt = f"""
        Create a comprehensive QA plan:
        
        Project: {task.description}
        
        Include:
        1. Quality objectives
        2. Testing strategy
        3. Quality metrics
        4. Review processes
        5. Tools and resources
        6. Timeline and milestones
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "qa_plan": response,
            "created_at": datetime.now().isoformat()
        }
    
    async def _general_qa_task(self, task: Task) -> Dict[str, Any]:
        """一般的なQAタスク"""
        prompt = f"As a QA engineer, please handle this task: {task.description}"
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "response": response
        }

class TesterAgent(BaseAgent):
    """テスターエージェント"""
    
    def _initialize_role_specific(self):
        self.capabilities = [
            "test_execution",
            "test_case_creation",
            "bug_reporting",
            "automation_testing",
            "performance_testing"
        ]
    
    def _get_role_context(self) -> Dict[str, Any]:
        return {
            "title": "Software Tester",
            "description": "Responsible for testing software functionality and finding bugs",
            "responsibilities": [
                "Create and execute test cases",
                "Perform functional and non-functional testing",
                "Report and track bugs",
                "Automate test scenarios",
                "Validate fixes and improvements",
                "Ensure software meets requirements"
            ]
        }
    
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """テスタータスクを処理"""
        try:
            if "test" in task.description.lower():
                return await self._execute_tests(task)
            elif "case" in task.description.lower():
                return await self._create_test_cases(task)
            elif "bug" in task.description.lower():
                return await self._report_bug(task)
            elif "automate" in task.description.lower():
                return await self._automate_tests(task)
            else:
                return await self._general_testing_task(task)
                
        except Exception as e:
            logger.error(f"Tester task processing error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_tests(self, task: Task) -> Dict[str, Any]:
        """テストを実行"""
        prompt = f"""
        Execute comprehensive testing for:
        
        Feature/Component: {task.description}
        
        Perform:
        1. Functional testing
        2. Edge case testing
        3. Error handling testing
        4. Integration testing
        5. Performance testing
        6. Security testing
        
        Report results with pass/fail status and any issues found.
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "test_results": response,
            "tests_passed": 85,  # 仮の成功率
            "tests_failed": 15,
            "executed_at": datetime.now().isoformat()
        }
    
    async def _create_test_cases(self, task: Task) -> Dict[str, Any]:
        """テストケースを作成"""
        prompt = f"""
        Create comprehensive test cases for:
        
        Requirements: {task.description}
        
        For each test case, provide:
        1. Test case ID
        2. Test description
        3. Preconditions
        4. Test steps
        5. Expected results
        6. Priority level
        7. Test data requirements
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "test_cases": response,
            "total_cases": 25,  # 仮の数
            "created_at": datetime.now().isoformat()
        }
    
    async def _report_bug(self, task: Task) -> Dict[str, Any]:
        """バグを報告"""
        prompt = f"""
        Create a detailed bug report for:
        
        Issue: {task.description}
        
        Include:
        1. Bug summary
        2. Steps to reproduce
        3. Expected vs actual behavior
        4. Environment details
        5. Severity and priority
        6. Screenshots/logs if applicable
        7. Workaround if available
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "bug_report": response,
            "severity": "medium",  # 仮の重要度
            "reported_at": datetime.now().isoformat()
        }
    
    async def _automate_tests(self, task: Task) -> Dict[str, Any]:
        """テストを自動化"""
        prompt = f"""
        Create automated test scripts for:
        
        Test Scenario: {task.description}
        
        Provide:
        1. Test automation framework selection
        2. Automated test scripts
        3. Test data setup
        4. Execution instructions
        5. Reporting mechanism
        6. Maintenance guidelines
        """
        
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "automation_scripts": response,
            "automated_at": datetime.now().isoformat()
        }
    
    async def _general_testing_task(self, task: Task) -> Dict[str, Any]:
        """一般的なテストタスク"""
        prompt = f"As a software tester, please handle this task: {task.description}"
        response = await self.generate_response(prompt, {"task": asdict(task)})
        
        return {
            "status": "success",
            "response": response
        }

class MultiAgentOrchestrator:
    """マルチエージェントオーケストレーター"""
    
    def __init__(self, qwq_engine):
        self.qwq_engine = qwq_engine
        self.agents: Dict[str, BaseAgent] = {}
        self.tasks: Dict[str, Task] = {}
        self.message_queue = asyncio.Queue()
        self.is_running = False
        
        # 統計情報
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "active_agents": 0,
            "messages_sent": 0
        }
        
        # エージェントを初期化
        self._initialize_agents()
    
    def _initialize_agents(self):
        """エージェントを初期化"""
        # PM エージェント
        pm_agent = ProjectManagerAgent("pm_001", AgentRole.PROJECT_MANAGER, self.qwq_engine)
        self.agents["pm_001"] = pm_agent
        
        # PG エージェント
        pg_agent = ProgrammerAgent("pg_001", AgentRole.PROGRAMMER, self.qwq_engine)
        self.agents["pg_001"] = pg_agent
        
        # QA エージェント
        qa_agent = QAEngineerAgent("qa_001", AgentRole.QA_ENGINEER, self.qwq_engine)
        self.agents["qa_001"] = qa_agent
        
        # テスター エージェント
        tester_agent = TesterAgent("tester_001", AgentRole.TESTER, self.qwq_engine)
        self.agents["tester_001"] = tester_agent
        
        logger.info(f"Initialized {len(self.agents)} agents")
    
    async def start(self):
        """オーケストレーターを開始"""
        self.is_running = True
        
        # メッセージ処理ループを開始
        asyncio.create_task(self._message_processing_loop())
        
        logger.info("Multi-agent orchestrator started")
    
    async def stop(self):
        """オーケストレーターを停止"""
        self.is_running = False
        logger.info("Multi-agent orchestrator stopped")
    
    async def submit_task(self, title: str, description: str, 
                         role: AgentRole, priority: TaskPriority = TaskPriority.MEDIUM) -> str:
        """タスクを投入"""
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            role=role,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.tasks[task.id] = task
        self.stats["total_tasks"] += 1
        
        # 適切なエージェントにタスクを割り当て
        await self._assign_task(task)
        
        logger.info(f"Task submitted: {task.id} - {task.title}")
        return task.id
    
    async def _assign_task(self, task: Task):
        """タスクをエージェントに割り当て"""
        # 役割に基づいてエージェントを選択
        suitable_agents = [agent for agent in self.agents.values() 
                          if agent.role == task.role and agent.is_active]
        
        if not suitable_agents:
            logger.error(f"No suitable agent found for task {task.id}")
            task.status = TaskStatus.FAILED
            return
        
        # 最も負荷の少ないエージェントを選択（簡単な実装）
        selected_agent = min(suitable_agents, 
                           key=lambda a: a.performance_metrics["tasks_completed"])
        
        task.assigned_agent = selected_agent.agent_id
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now().isoformat()
        
        # エージェントにタスクを送信
        await self._send_task_to_agent(selected_agent, task)
    
    async def _send_task_to_agent(self, agent: BaseAgent, task: Task):
        """エージェントにタスクを送信"""
        try:
            start_time = time.time()
            
            # タスクを処理
            result = await agent.process_task(task)
            
            completion_time = int((time.time() - start_time) * 60)  # 分単位
            
            # 結果に基づいてタスクステータスを更新
            if result.get("status") == "success":
                task.status = TaskStatus.COMPLETED
                task.actual_time = completion_time
                task.deliverables = result.get("deliverables", [])
                self.stats["completed_tasks"] += 1
                
                # パフォーマンス指標を更新
                quality_score = result.get("quality_score", 80.0)
                agent.update_performance_metrics(task, completion_time, quality_score)
                
            else:
                task.status = TaskStatus.FAILED
                self.stats["failed_tasks"] += 1
                agent.update_performance_metrics(task, completion_time, 0.0)
            
            task.updated_at = datetime.now().isoformat()
            
            # 結果をタスクに記録
            task.feedback.append({
                "agent_id": agent.agent_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Task {task.id} completed by {agent.agent_id}: {task.status.value}")
            
        except Exception as e:
            logger.error(f"Error processing task {task.id}: {e}")
            task.status = TaskStatus.FAILED
            task.updated_at = datetime.now().isoformat()
    
    async def _message_processing_loop(self):
        """メッセージ処理ループ"""
        while self.is_running:
            try:
                # メッセージを取得（タイムアウト付き）
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # メッセージを適切なエージェントに配信
                if message.to_agent in self.agents:
                    await self.agents[message.to_agent].receive_message(message)
                    self.stats["messages_sent"] += 1
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """タスクステータスを取得"""
        if task_id in self.tasks:
            return asdict(self.tasks[task_id])
        return None
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """エージェントステータスを取得"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            return {
                "agent_id": agent.agent_id,
                "role": agent.role.value,
                "is_active": agent.is_active,
                "current_task": agent.current_task,
                "capabilities": agent.capabilities,
                "performance_metrics": agent.performance_metrics
            }
        return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム全体のステータスを取得"""
        active_agents = sum(1 for agent in self.agents.values() if agent.is_active)
        
        return {
            "is_running": self.is_running,
            "total_agents": len(self.agents),
            "active_agents": active_agents,
            "total_tasks": len(self.tasks),
            "stats": self.stats,
            "agents": {agent_id: self.get_agent_status(agent_id) 
                      for agent_id in self.agents.keys()}
        }


# グローバルマルチエージェントシステム
_multi_agent_system = None

def get_multi_agent_system() -> MultiAgentOrchestrator:
    """マルチエージェントシステムのシングルトンインスタンス取得"""
    global _multi_agent_system
    return _multi_agent_system

async def initialize_multi_agent_system(qwq_engine) -> MultiAgentOrchestrator:
    """マルチエージェントシステムを初期化"""
    global _multi_agent_system
    _multi_agent_system = MultiAgentOrchestrator(qwq_engine)
    await _multi_agent_system.start()
    return _multi_agent_system

