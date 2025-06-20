"""
AIエージェント - メインエージェントクラス

このモジュールは、タスク計画、実行、学習機能を統合した
メインのAIエージェントクラスを実装します。
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json

from task_planner import TaskPlanner, DependencyGraph
from execution_engine import ExecutionEngine
from tools.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class ExecutionHistory:
    """過去の実行結果を記録"""
    
    def __init__(self):
        self.executions: List[Dict[str, Any]] = []
        self.success_patterns: Dict[str, int] = {}
        self.failure_patterns: Dict[str, int] = {}
    
    def record_execution(self, execution_result: Dict[str, Any]):
        """実行結果を記録"""
        self.executions.append({
            **execution_result,
            'recorded_at': datetime.now().isoformat()
        })
        
        # パターン分析
        self._analyze_patterns(execution_result)
    
    def _analyze_patterns(self, execution_result: Dict[str, Any]):
        """実行パターンを分析"""
        status = execution_result.get('status', 'unknown')
        task_status = execution_result.get('task_status', {})
        
        # 成功・失敗パターンを記録
        for task in task_status.get('tasks', []):
            tool_name = task.get('tool_name', 'unknown')
            task_status_value = task.get('status', 'unknown')
            
            pattern_key = f"{tool_name}_{task_status_value}"
            
            if task_status_value == 'completed':
                self.success_patterns[pattern_key] = self.success_patterns.get(pattern_key, 0) + 1
            elif task_status_value == 'failed':
                self.failure_patterns[pattern_key] = self.failure_patterns.get(pattern_key, 0) + 1
    
    def get_success_rate(self, tool_name: str) -> float:
        """ツールの成功率を取得"""
        success_count = self.success_patterns.get(f"{tool_name}_completed", 0)
        failure_count = self.failure_patterns.get(f"{tool_name}_failed", 0)
        total = success_count + failure_count
        
        if total == 0:
            return 0.0
        
        return success_count / total
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """実行統計を取得"""
        total_executions = len(self.executions)
        successful_executions = len([e for e in self.executions if e.get('status') == 'completed'])
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': successful_executions / total_executions if total_executions > 0 else 0.0,
            'success_patterns': self.success_patterns,
            'failure_patterns': self.failure_patterns
        }

class PatternAnalyzer:
    """成功・失敗パターンの分析"""
    
    def __init__(self, execution_history: ExecutionHistory):
        self.execution_history = execution_history
    
    def analyze_request_patterns(self, request: str) -> Dict[str, Any]:
        """要求パターンを分析"""
        # 過去の類似要求を検索
        similar_executions = self._find_similar_executions(request)
        
        # 成功パターンを抽出
        success_patterns = self._extract_success_patterns(similar_executions)
        
        # 失敗パターンを抽出
        failure_patterns = self._extract_failure_patterns(similar_executions)
        
        return {
            'similar_executions': len(similar_executions),
            'success_patterns': success_patterns,
            'failure_patterns': failure_patterns,
            'recommendations': self._generate_recommendations(success_patterns, failure_patterns)
        }
    
    def _find_similar_executions(self, request: str) -> List[Dict[str, Any]]:
        """類似の実行履歴を検索"""
        # 簡単なキーワードベースの類似度計算
        request_words = set(request.lower().split())
        similar_executions = []
        
        for execution in self.execution_history.executions:
            # 実行ログから要求を抽出（簡略化）
            execution_request = execution.get('original_request', '')
            execution_words = set(execution_request.lower().split())
            
            # Jaccard類似度を計算
            intersection = len(request_words & execution_words)
            union = len(request_words | execution_words)
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0.3:  # 閾値
                    similar_executions.append({
                        **execution,
                        'similarity': similarity
                    })
        
        return sorted(similar_executions, key=lambda x: x['similarity'], reverse=True)
    
    def _extract_success_patterns(self, executions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """成功パターンを抽出"""
        success_patterns = []
        
        for execution in executions:
            if execution.get('status') == 'completed':
                task_status = execution.get('task_status', {})
                successful_tasks = [
                    task for task in task_status.get('tasks', [])
                    if task.get('status') == 'completed'
                ]
                
                if successful_tasks:
                    success_patterns.append({
                        'execution_id': execution.get('session_id'),
                        'tasks': successful_tasks,
                        'execution_time': execution.get('execution_time', 0),
                        'similarity': execution.get('similarity', 0)
                    })
        
        return success_patterns
    
    def _extract_failure_patterns(self, executions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """失敗パターンを抽出"""
        failure_patterns = []
        
        for execution in executions:
            if execution.get('status') == 'failed':
                task_status = execution.get('task_status', {})
                failed_tasks = [
                    task for task in task_status.get('tasks', [])
                    if task.get('status') == 'failed'
                ]
                
                if failed_tasks:
                    failure_patterns.append({
                        'execution_id': execution.get('session_id'),
                        'tasks': failed_tasks,
                        'error': execution.get('error'),
                        'similarity': execution.get('similarity', 0)
                    })
        
        return failure_patterns
    
    def _generate_recommendations(self, success_patterns: List[Dict[str, Any]], 
                                failure_patterns: List[Dict[str, Any]]) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        if success_patterns:
            # 最も成功率の高いツールを推奨
            tool_success_count = {}
            for pattern in success_patterns:
                for task in pattern['tasks']:
                    tool_name = task.get('tool_name', 'unknown')
                    tool_success_count[tool_name] = tool_success_count.get(tool_name, 0) + 1
            
            if tool_success_count:
                best_tool = max(tool_success_count, key=tool_success_count.get)
                recommendations.append(f"過去の成功例から、{best_tool}ツールの使用を推奨します")
        
        if failure_patterns:
            # よく失敗するツールを警告
            tool_failure_count = {}
            for pattern in failure_patterns:
                for task in pattern['tasks']:
                    tool_name = task.get('tool_name', 'unknown')
                    tool_failure_count[tool_name] = tool_failure_count.get(tool_name, 0) + 1
            
            if tool_failure_count:
                worst_tool = max(tool_failure_count, key=tool_failure_count.get)
                recommendations.append(f"{worst_tool}ツールは失敗しやすいため注意が必要です")
        
        return recommendations

class StrategyOptimizer:
    """実行戦略の最適化"""
    
    def __init__(self, pattern_analyzer: PatternAnalyzer):
        self.pattern_analyzer = pattern_analyzer
    
    def optimize_plan(self, plan: DependencyGraph, request: str) -> DependencyGraph:
        """実行計画を最適化"""
        # パターン分析結果を取得
        analysis = self.pattern_analyzer.analyze_request_patterns(request)
        
        # 成功パターンに基づいてタスクの優先度を調整
        self._adjust_task_priorities(plan, analysis['success_patterns'])
        
        # 失敗パターンに基づいてリスクの高いタスクを特定
        self._identify_risky_tasks(plan, analysis['failure_patterns'])
        
        # 代替手段を提案
        self._suggest_alternatives(plan, analysis['failure_patterns'])
        
        return plan
    
    def _adjust_task_priorities(self, plan: DependencyGraph, success_patterns: List[Dict[str, Any]]):
        """成功パターンに基づいてタスクの優先度を調整"""
        tool_success_scores = {}
        
        for pattern in success_patterns:
            for task in pattern['tasks']:
                tool_name = task.get('tool_name', 'unknown')
                execution_time = pattern.get('execution_time', 0)
                similarity = pattern.get('similarity', 0)
                
                # 成功スコア = 類似度 / 実行時間（短い方が良い）
                score = similarity / max(execution_time, 1)
                tool_success_scores[tool_name] = max(tool_success_scores.get(tool_name, 0), score)
        
        # タスクの優先度を調整
        for task in plan.nodes.values():
            tool_name = task.tool_name
            if tool_name in tool_success_scores:
                # 成功スコアが高いツールの優先度を上げる
                score = tool_success_scores[tool_name]
                if score > 0.5:
                    task.priority = task.priority.__class__(min(task.priority.value + 1, 4))
    
    def _identify_risky_tasks(self, plan: DependencyGraph, failure_patterns: List[Dict[str, Any]]):
        """失敗パターンに基づいてリスクの高いタスクを特定"""
        risky_tools = set()
        
        for pattern in failure_patterns:
            for task in pattern['tasks']:
                tool_name = task.get('tool_name', 'unknown')
                risky_tools.add(tool_name)
        
        # リスクの高いタスクの再試行回数を増やす
        for task in plan.nodes.values():
            if task.tool_name in risky_tools:
                task.max_retries = min(task.max_retries + 2, 5)
    
    def _suggest_alternatives(self, plan: DependencyGraph, failure_patterns: List[Dict[str, Any]]):
        """代替手段を提案"""
        # TODO: より高度な代替手段の提案ロジックを実装
        pass

class AIAgent:
    """メインのAIエージェントクラス"""
    
    def __init__(self, tool_manager: ToolManager):
        self.tool_manager = tool_manager
        self.task_planner = TaskPlanner()
        self.execution_engine = ExecutionEngine(tool_manager)
        self.execution_history = ExecutionHistory()
        self.pattern_analyzer = PatternAnalyzer(self.execution_history)
        self.strategy_optimizer = StrategyOptimizer(self.pattern_analyzer)
        
        # 利用可能なツールを登録
        self._register_available_tools()
    
    def _register_available_tools(self):
        """利用可能なツールを登録"""
        # TODO: ツールマネージャーから利用可能なツールを取得して登録
        available_tools = {
            'browser': {'description': 'ブラウザ自動化ツール', 'category': 'web'},
            'file_editor': {'description': 'ファイル編集ツール', 'category': 'file'},
            'code_executor': {'description': 'コード実行ツール', 'category': 'code'},
            'image_generator': {'description': '画像生成ツール', 'category': 'media'},
            'text_processor': {'description': 'テキスト処理ツール', 'category': 'text'}
        }
        
        for tool_name, tool_info in available_tools.items():
            self.task_planner.register_tool(tool_name, tool_info)
    
    async def process_request(self, user_request: str, session_id: str, user_id: str) -> Dict[str, Any]:
        """ユーザーの要求を処理"""
        try:
            # 1. 要求を分析
            logger.info(f"[{session_id}] 要求分析開始: {user_request}")
            
            # 2. 実行計画を作成
            plan = self.task_planner.create_execution_plan(user_request)
            logger.info(f"[{session_id}] 実行計画作成完了: {len(plan.nodes)}個のタスク")
            
            # 3. 過去のパターンに基づいて計画を最適化
            optimized_plan = self.strategy_optimizer.optimize_plan(plan, user_request)
            logger.info(f"[{session_id}] 実行計画最適化完了")
            
            # 4. 実行計画を実行
            execution_result = await self.execution_engine.execute_plan(
                optimized_plan, session_id, user_id
            )
            
            # 5. 実行結果を記録
            execution_result['original_request'] = user_request
            self.execution_history.record_execution(execution_result)
            
            logger.info(f"[{session_id}] 要求処理完了: {execution_result['status']}")
            
            return execution_result
            
        except Exception as e:
            logger.error(f"[{session_id}] 要求処理エラー: {str(e)}")
            
            error_result = {
                'session_id': session_id,
                'status': 'error',
                'error': str(e),
                'original_request': user_request
            }
            
            self.execution_history.record_execution(error_result)
            
            return error_result
    
    def add_progress_callback(self, callback: Callable):
        """進捗更新のコールバックを追加"""
        self.execution_engine.add_progress_callback(callback)
    
    def get_execution_status(self, session_id: str) -> Dict[str, Any]:
        """実行状況を取得"""
        return self.execution_engine.get_execution_status(session_id)
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """実行統計を取得"""
        return self.execution_history.get_execution_statistics()
    
    async def cancel_execution(self, session_id: str):
        """実行をキャンセル"""
        await self.execution_engine.cancel_execution(session_id)
    
    def analyze_request_patterns(self, request: str) -> Dict[str, Any]:
        """要求パターンを分析"""
        return self.pattern_analyzer.analyze_request_patterns(request)

