"""
Advanced Task Decomposer - 高度なタスク分解エンジン

このモジュールは、複雑なタスクをより効率的に分解し、
依存関係を分析し、最適な実行順序を決定します。
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import networkx as nx
import json
import re

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """タスクタイプ"""
    RESEARCH = "research"
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"

class Priority(Enum):
    """優先度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TaskNode:
    """タスクノード"""
    id: str
    title: str
    description: str
    task_type: TaskType
    priority: Priority
    estimated_time: int  # 分
    complexity: int  # 1-10
    dependencies: List[str]
    required_skills: List[str]
    tools: List[str]
    acceptance_criteria: List[str]
    risks: List[str]

class AdvancedTaskDecomposer:
    """
    高度なタスク分解エンジン
    
    機能:
    - 複雑なタスクの階層的分解
    - 依存関係の自動分析
    - 最適な実行順序の決定
    - リスク分析と軽減策の提案
    - 並列実行可能性の判定
    """
    
    def __init__(self, qwen_engine):
        """
        タスク分解エンジンを初期化
        
        Args:
            qwen_engine: Qwenエンジンインスタンス
        """
        self.qwen_engine = qwen_engine
        
        # タスクパターンの定義
        self.task_patterns = self._load_task_patterns()
        
        # スキルマップ
        self.skill_map = {
            "python": ["coding", "testing", "debugging"],
            "javascript": ["coding", "frontend", "testing"],
            "react": ["frontend", "ui", "components"],
            "flask": ["backend", "api", "web"],
            "docker": ["deployment", "containerization"],
            "git": ["version_control", "collaboration"],
            "testing": ["quality_assurance", "validation"],
            "documentation": ["writing", "communication"]
        }
    
    def decompose_complex_task(
        self, 
        task_description: str,
        context: Dict[str, Any] = None,
        max_depth: int = 3
    ) -> List[TaskNode]:
        """
        複雑なタスクを階層的に分解
        
        Args:
            task_description: タスクの説明
            context: 追加のコンテキスト情報
            max_depth: 最大分解深度
            
        Returns:
            分解されたタスクノードのリスト
        """
        try:
            logger.info(f"Decomposing complex task: {task_description}")
            
            # 初期分析
            analysis = self._analyze_task_complexity(task_description, context)
            
            # 階層的分解
            task_nodes = self._hierarchical_decomposition(
                task_description, 
                analysis, 
                max_depth
            )
            
            # 依存関係の分析と最適化
            optimized_nodes = self._optimize_dependencies(task_nodes)
            
            # 実行順序の決定
            ordered_nodes = self._determine_execution_order(optimized_nodes)
            
            logger.info(f"Task decomposed into {len(ordered_nodes)} nodes")
            return ordered_nodes
            
        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            return []
    
    def _analyze_task_complexity(
        self, 
        task_description: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """タスクの複雑さを分析"""
        
        analysis_prompt = f"""
以下のタスクを分析してください：

タスク: {task_description}
コンテキスト: {json.dumps(context or {}, ensure_ascii=False)}

以下の観点から分析し、JSON形式で回答してください：

{{
  "complexity_score": "1-10の複雑さスコア",
  "estimated_duration": "推定所要時間（時間）",
  "main_categories": ["主要なカテゴリ"],
  "required_technologies": ["必要な技術"],
  "potential_challenges": ["予想される課題"],
  "success_criteria": ["成功基準"],
  "deliverables": ["成果物"],
  "stakeholders": ["関係者"]
}}
"""
        
        try:
            response = self.qwen_engine.generate_text(analysis_prompt)
            
            # JSONの抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            else:
                logger.warning("Failed to parse task analysis JSON")
                return {}
                
        except Exception as e:
            logger.error(f"Task analysis failed: {e}")
            return {}
    
    def _hierarchical_decomposition(
        self, 
        task_description: str, 
        analysis: Dict[str, Any], 
        max_depth: int,
        current_depth: int = 0
    ) -> List[TaskNode]:
        """階層的にタスクを分解"""
        
        if current_depth >= max_depth:
            return []
        
        decomposition_prompt = f"""
以下のタスクを実行可能な小さなタスクに分解してください：

タスク: {task_description}
複雑さ: {analysis.get('complexity_score', 'unknown')}
技術要件: {analysis.get('required_technologies', [])}

各サブタスクを以下のJSON形式で出力してください：

{{
  "subtasks": [
    {{
      "id": "ユニークID",
      "title": "タスクタイトル",
      "description": "詳細な説明",
      "type": "research|planning|coding|testing|documentation|deployment|debugging|refactoring",
      "priority": "low|medium|high|critical",
      "estimated_time": "推定時間（分）",
      "complexity": "1-10の複雑さ",
      "dependencies": ["依存するタスクのID"],
      "required_skills": ["必要なスキル"],
      "tools": ["使用するツール"],
      "acceptance_criteria": ["受け入れ基準"],
      "risks": ["リスク要因"]
    }}
  ]
}}
"""
        
        try:
            response = self.qwen_engine.generate_text(decomposition_prompt)
            
            # JSONの抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return []
            
            data = json.loads(json_match.group())
            subtasks = data.get('subtasks', [])
            
            task_nodes = []
            for subtask in subtasks:
                node = TaskNode(
                    id=subtask.get('id', f"task_{len(task_nodes)}"),
                    title=subtask.get('title', ''),
                    description=subtask.get('description', ''),
                    task_type=TaskType(subtask.get('type', 'coding')),
                    priority=Priority[subtask.get('priority', 'medium').upper()],
                    estimated_time=int(subtask.get('estimated_time', 30)),
                    complexity=int(subtask.get('complexity', 5)),
                    dependencies=subtask.get('dependencies', []),
                    required_skills=subtask.get('required_skills', []),
                    tools=subtask.get('tools', []),
                    acceptance_criteria=subtask.get('acceptance_criteria', []),
                    risks=subtask.get('risks', [])
                )
                task_nodes.append(node)
            
            # 複雑なタスクをさらに分解
            additional_nodes = []
            for node in task_nodes:
                if node.complexity > 7 and current_depth < max_depth - 1:
                    sub_nodes = self._hierarchical_decomposition(
                        node.description,
                        {"complexity_score": node.complexity},
                        max_depth,
                        current_depth + 1
                    )
                    additional_nodes.extend(sub_nodes)
            
            task_nodes.extend(additional_nodes)
            return task_nodes
            
        except Exception as e:
            logger.error(f"Hierarchical decomposition failed: {e}")
            return []
    
    def _optimize_dependencies(self, task_nodes: List[TaskNode]) -> List[TaskNode]:
        """依存関係を最適化"""
        
        # 依存関係グラフを構築
        graph = nx.DiGraph()
        
        # ノードを追加
        for node in task_nodes:
            graph.add_node(node.id, node=node)
        
        # エッジを追加
        for node in task_nodes:
            for dep_id in node.dependencies:
                if dep_id in [n.id for n in task_nodes]:
                    graph.add_edge(dep_id, node.id)
        
        # 循環依存をチェック
        if not nx.is_directed_acyclic_graph(graph):
            logger.warning("Circular dependencies detected, attempting to resolve")
            
            # 循環を検出して解決
            cycles = list(nx.simple_cycles(graph))
            for cycle in cycles:
                # 最も優先度の低いエッジを削除
                min_priority_edge = None
                min_priority = float('inf')
                
                for i in range(len(cycle)):
                    from_node = cycle[i]
                    to_node = cycle[(i + 1) % len(cycle)]
                    
                    from_task = next(n for n in task_nodes if n.id == from_node)
                    priority_score = from_task.priority.value
                    
                    if priority_score < min_priority:
                        min_priority = priority_score
                        min_priority_edge = (from_node, to_node)
                
                if min_priority_edge:
                    graph.remove_edge(*min_priority_edge)
                    
                    # タスクノードからも依存関係を削除
                    to_task = next(n for n in task_nodes if n.id == min_priority_edge[1])
                    if min_priority_edge[0] in to_task.dependencies:
                        to_task.dependencies.remove(min_priority_edge[0])
        
        return task_nodes
    
    def _determine_execution_order(self, task_nodes: List[TaskNode]) -> List[TaskNode]:
        """最適な実行順序を決定"""
        
        # 依存関係グラフを再構築
        graph = nx.DiGraph()
        
        for node in task_nodes:
            graph.add_node(node.id, node=node)
        
        for node in task_nodes:
            for dep_id in node.dependencies:
                if dep_id in [n.id for n in task_nodes]:
                    graph.add_edge(dep_id, node.id)
        
        # トポロジカルソート
        try:
            ordered_ids = list(nx.topological_sort(graph))
            
            # 優先度とクリティカルパスを考慮した調整
            ordered_nodes = []
            for node_id in ordered_ids:
                node = next(n for n in task_nodes if n.id == node_id)
                ordered_nodes.append(node)
            
            # 同じレベルのタスクは優先度順にソート
            return self._sort_by_priority_and_critical_path(ordered_nodes, graph)
            
        except nx.NetworkXError as e:
            logger.error(f"Failed to determine execution order: {e}")
            return task_nodes
    
    def _sort_by_priority_and_critical_path(
        self, 
        nodes: List[TaskNode], 
        graph: nx.DiGraph
    ) -> List[TaskNode]:
        """優先度とクリティカルパスを考慮してソート"""
        
        # クリティカルパスを計算
        critical_paths = {}
        for node in nodes:
            try:
                # このノードから終端までの最長パス
                paths = []
                for end_node in [n for n in graph.nodes() if graph.out_degree(n) == 0]:
                    if nx.has_path(graph, node.id, end_node):
                        path_length = nx.shortest_path_length(graph, node.id, end_node)
                        paths.append(path_length)
                
                critical_paths[node.id] = max(paths) if paths else 0
                
            except nx.NetworkXError:
                critical_paths[node.id] = 0
        
        # 優先度とクリティカルパスでソート
        def sort_key(node):
            return (
                -node.priority.value,  # 高優先度を先に
                -critical_paths.get(node.id, 0),  # クリティカルパス上を先に
                node.estimated_time  # 短時間タスクを先に
            )
        
        return sorted(nodes, key=sort_key)
    
    def analyze_parallel_execution(self, task_nodes: List[TaskNode]) -> Dict[str, Any]:
        """並列実行可能性を分析"""
        
        # 依存関係グラフを構築
        graph = nx.DiGraph()
        
        for node in task_nodes:
            graph.add_node(node.id)
        
        for node in task_nodes:
            for dep_id in node.dependencies:
                if dep_id in [n.id for n in task_nodes]:
                    graph.add_edge(dep_id, node.id)
        
        # レベル別にグループ化（並列実行可能なタスクグループ）
        levels = {}
        processed = set()
        
        level = 0
        while len(processed) < len(task_nodes):
            current_level = []
            
            for node in task_nodes:
                if node.id in processed:
                    continue
                
                # 依存関係がすべて処理済みかチェック
                deps_satisfied = all(dep in processed for dep in node.dependencies)
                
                if deps_satisfied:
                    current_level.append(node.id)
            
            if current_level:
                levels[f"level_{level}"] = current_level
                processed.update(current_level)
                level += 1
            else:
                # デッドロック状態
                break
        
        # 並列実行グループの詳細分析
        parallel_groups = []
        for level_name, node_ids in levels.items():
            if len(node_ids) > 1:  # 複数のタスクが並列実行可能
                group_nodes = [n for n in task_nodes if n.id in node_ids]
                
                # リソース競合をチェック
                resource_conflicts = self._check_resource_conflicts(group_nodes)
                
                # 最適な並列グループを作成
                optimal_groups = self._create_optimal_parallel_groups(group_nodes, resource_conflicts)
                
                for group in optimal_groups:
                    parallel_groups.append({
                        'level': level_name,
                        'task_ids': [n.id for n in group],
                        'estimated_time': max(n.estimated_time for n in group),
                        'total_complexity': sum(n.complexity for n in group),
                        'resource_requirements': self._get_resource_requirements(group)
                    })
            else:
                # 単一タスク
                node = next(n for n in task_nodes if n.id in node_ids)
                parallel_groups.append({
                    'level': level_name,
                    'task_ids': node_ids,
                    'estimated_time': node.estimated_time,
                    'total_complexity': node.complexity,
                    'resource_requirements': self._get_resource_requirements([node])
                })
        
        return {
            'levels': levels,
            'parallel_groups': parallel_groups,
            'max_parallelism': max(len(node_ids) for node_ids in levels.values()) if levels else 1,
            'total_levels': len(levels)
        }
    
    def _check_resource_conflicts(self, nodes: List[TaskNode]) -> Dict[str, List[str]]:
        """リソース競合をチェック"""
        conflicts = {}
        
        # ツール競合をチェック
        tool_usage = {}
        for node in nodes:
            for tool in node.tools:
                if tool not in tool_usage:
                    tool_usage[tool] = []
                tool_usage[tool].append(node.id)
        
        for tool, users in tool_usage.items():
            if len(users) > 1:
                conflicts[f"tool_{tool}"] = users
        
        # スキル競合をチェック（同じ専門スキルを要求するタスク）
        skill_usage = {}
        for node in nodes:
            for skill in node.required_skills:
                if skill not in skill_usage:
                    skill_usage[skill] = []
                skill_usage[skill].append(node.id)
        
        for skill, users in skill_usage.items():
            if len(users) > 1 and skill in ['database', 'file_system', 'network']:
                conflicts[f"skill_{skill}"] = users
        
        return conflicts
    
    def _create_optimal_parallel_groups(
        self, 
        nodes: List[TaskNode], 
        conflicts: Dict[str, List[str]]
    ) -> List[List[TaskNode]]:
        """最適な並列グループを作成"""
        
        if not conflicts:
            # 競合がない場合、すべて並列実行可能
            return [nodes]
        
        # 競合を避けるグループ分け
        groups = []
        remaining_nodes = nodes.copy()
        
        while remaining_nodes:
            current_group = []
            used_resources = set()
            
            for node in remaining_nodes.copy():
                # このノードが現在のグループと競合するかチェック
                node_resources = set(node.tools + node.required_skills)
                
                if not (node_resources & used_resources):
                    current_group.append(node)
                    used_resources.update(node_resources)
                    remaining_nodes.remove(node)
            
            if current_group:
                groups.append(current_group)
            else:
                # デッドロック回避：残りのノードを強制的に追加
                groups.append([remaining_nodes.pop(0)])
        
        return groups
    
    def _get_resource_requirements(self, nodes: List[TaskNode]) -> Dict[str, Any]:
        """リソース要件を取得"""
        all_tools = set()
        all_skills = set()
        max_complexity = 0
        total_time = 0
        
        for node in nodes:
            all_tools.update(node.tools)
            all_skills.update(node.required_skills)
            max_complexity = max(max_complexity, node.complexity)
            total_time += node.estimated_time
        
        return {
            'tools': list(all_tools),
            'skills': list(all_skills),
            'max_complexity': max_complexity,
            'total_time': total_time,
            'cpu_intensive': any('compilation' in node.tools or 'testing' in node.tools for node in nodes),
            'io_intensive': any('file_system' in node.tools or 'database' in node.tools for node in nodes)
        }
    
    def estimate_total_time(
        self, 
        task_nodes: List[TaskNode], 
        parallel_levels: Dict[str, List[str]] = None
    ) -> Dict[str, int]:
        """総実行時間を推定"""
        
        if not parallel_levels:
            parallel_levels = self.analyze_parallel_execution(task_nodes)
        
        sequential_time = sum(node.estimated_time for node in task_nodes)
        
        parallel_time = 0
        for level_nodes in parallel_levels.values():
            level_times = [
                next(n.estimated_time for n in task_nodes if n.id == node_id)
                for node_id in level_nodes
            ]
            parallel_time += max(level_times) if level_times else 0
        
        return {
            "sequential_time": sequential_time,
            "parallel_time": parallel_time,
            "time_saved": sequential_time - parallel_time,
            "efficiency_gain": (sequential_time - parallel_time) / sequential_time if sequential_time > 0 else 0
        }
    
    def _load_task_patterns(self) -> Dict[str, Any]:
        """タスクパターンを読み込み"""
        return {
            "web_development": {
                "patterns": [
                    "setup_environment",
                    "create_project_structure", 
                    "implement_backend",
                    "implement_frontend",
                    "integrate_components",
                    "testing",
                    "deployment"
                ],
                "technologies": ["html", "css", "javascript", "python", "flask", "react"]
            },
            "data_analysis": {
                "patterns": [
                    "data_collection",
                    "data_cleaning",
                    "exploratory_analysis",
                    "modeling",
                    "validation",
                    "visualization",
                    "reporting"
                ],
                "technologies": ["python", "pandas", "numpy", "matplotlib", "jupyter"]
            },
            "api_development": {
                "patterns": [
                    "api_design",
                    "endpoint_implementation",
                    "authentication",
                    "validation",
                    "testing",
                    "documentation",
                    "deployment"
                ],
                "technologies": ["python", "flask", "fastapi", "swagger", "postman"]
            }
        }
    
    def suggest_improvements(self, task_nodes: List[TaskNode]) -> List[str]:
        """タスク分解の改善提案"""
        suggestions = []
        
        # 複雑すぎるタスクをチェック
        complex_tasks = [n for n in task_nodes if n.complexity > 8]
        if complex_tasks:
            suggestions.append(
                f"{len(complex_tasks)}個の高複雑度タスクをさらに分解することを推奨します"
            )
        
        # 長時間タスクをチェック
        long_tasks = [n for n in task_nodes if n.estimated_time > 120]
        if long_tasks:
            suggestions.append(
                f"{len(long_tasks)}個の長時間タスク（2時間以上）を分割することを推奨します"
            )
        
        # 依存関係の多いタスクをチェック
        high_dependency_tasks = [n for n in task_nodes if len(n.dependencies) > 3]
        if high_dependency_tasks:
            suggestions.append(
                f"{len(high_dependency_tasks)}個のタスクが多くの依存関係を持っています。設計を見直すことを推奨します"
            )
        
        # 並列実行の機会をチェック
        parallel_levels = self.analyze_parallel_execution(task_nodes)
        max_parallel = max(len(nodes) for nodes in parallel_levels.values())
        if max_parallel < 2:
            suggestions.append("並列実行の機会が少ないです。依存関係を見直して並列化を検討してください")
        
        return suggestions

