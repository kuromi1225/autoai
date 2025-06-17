"""
Plan Reviewer - 実行計画の事前確認と修正依頼システム

このモジュールは、エージェントが実行計画を立てた際に、
ユーザーに事前確認を求め、修正依頼を受け付ける機能を提供します。
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class PlanStatus(Enum):
    """計画のステータス"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class PlanStep:
    """実行計画のステップ"""
    id: str
    title: str
    description: str
    type: str  # code, file_operation, web_search, etc.
    estimated_time: int  # 推定時間（秒）
    dependencies: List[str]  # 依存するステップのID
    tools: List[str]  # 使用するツール
    parameters: Dict[str, Any]  # ステップのパラメータ
    risk_level: str  # low, medium, high
    reversible: bool  # 元に戻せるかどうか
    
class ExecutionPlan:
    """実行計画クラス"""
    
    def __init__(
        self,
        plan_id: str,
        title: str,
        description: str,
        steps: List[PlanStep],
        estimated_total_time: int,
        risk_assessment: Dict[str, Any]
    ):
        self.plan_id = plan_id
        self.title = title
        self.description = description
        self.steps = steps
        self.estimated_total_time = estimated_total_time
        self.risk_assessment = risk_assessment
        self.status = PlanStatus.DRAFT
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.user_feedback = []
        self.modifications = []
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'plan_id': self.plan_id,
            'title': self.title,
            'description': self.description,
            'steps': [asdict(step) for step in self.steps],
            'estimated_total_time': self.estimated_total_time,
            'risk_assessment': self.risk_assessment,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_feedback': self.user_feedback,
            'modifications': self.modifications
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionPlan':
        """辞書から復元"""
        steps = [PlanStep(**step_data) for step_data in data['steps']]
        
        plan = cls(
            plan_id=data['plan_id'],
            title=data['title'],
            description=data['description'],
            steps=steps,
            estimated_total_time=data['estimated_total_time'],
            risk_assessment=data['risk_assessment']
        )
        
        plan.status = PlanStatus(data['status'])
        plan.created_at = datetime.fromisoformat(data['created_at'])
        plan.updated_at = datetime.fromisoformat(data['updated_at'])
        plan.user_feedback = data.get('user_feedback', [])
        plan.modifications = data.get('modifications', [])
        
        return plan

class PlanReviewer:
    """
    実行計画の事前確認と修正依頼を管理するクラス
    
    主な機能:
    - 実行計画の生成
    - ユーザーへの確認依頼
    - 修正依頼の処理
    - 計画の承認・却下
    """
    
    def __init__(self, storage_dir: str = "/app/data/plans"):
        """
        PlanReviewerを初期化
        
        Args:
            storage_dir: 計画保存ディレクトリ
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # アクティブな計画を管理
        self.active_plans: Dict[str, ExecutionPlan] = {}
        
        # 計画テンプレート
        self.plan_templates = self._load_plan_templates()
        
        logger.info(f"PlanReviewer initialized with storage: {storage_dir}")
    
    def create_plan(
        self,
        task_description: str,
        context: Dict[str, Any] = None,
        user_preferences: Dict[str, Any] = None
    ) -> ExecutionPlan:
        """
        タスクから実行計画を生成
        
        Args:
            task_description: タスクの説明
            context: コンテキスト情報
            user_preferences: ユーザー設定
            
        Returns:
            生成された実行計画
        """
        try:
            # 計画IDの生成
            plan_id = f"plan_{int(datetime.utcnow().timestamp())}"
            
            # タスクを分析してステップに分解
            steps = self._decompose_task(task_description, context)
            
            # リスク評価
            risk_assessment = self._assess_risks(steps)
            
            # 推定時間の計算
            estimated_total_time = sum(step.estimated_time for step in steps)
            
            # 実行計画の作成
            plan = ExecutionPlan(
                plan_id=plan_id,
                title=self._generate_plan_title(task_description),
                description=task_description,
                steps=steps,
                estimated_total_time=estimated_total_time,
                risk_assessment=risk_assessment
            )
            
            # 計画の保存
            self._save_plan(plan)
            self.active_plans[plan_id] = plan
            
            logger.info(f"Plan created: {plan_id} with {len(steps)} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            raise
    
    def submit_for_review(self, plan_id: str) -> Dict[str, Any]:
        """
        計画をレビュー待ちにする
        
        Args:
            plan_id: 計画ID
            
        Returns:
            レビュー依頼情報
        """
        try:
            plan = self.active_plans.get(plan_id)
            if not plan:
                raise ValueError(f"Plan not found: {plan_id}")
            
            plan.status = PlanStatus.PENDING_REVIEW
            plan.updated_at = datetime.utcnow()
            
            # レビュー依頼の生成
            review_request = {
                'plan_id': plan_id,
                'title': plan.title,
                'description': plan.description,
                'steps_summary': self._generate_steps_summary(plan.steps),
                'estimated_time': plan.estimated_total_time,
                'risk_level': plan.risk_assessment.get('overall_risk', 'medium'),
                'high_risk_steps': self._get_high_risk_steps(plan.steps),
                'irreversible_steps': self._get_irreversible_steps(plan.steps),
                'confirmation_required': True,
                'review_url': f"/review/{plan_id}"
            }
            
            self._save_plan(plan)
            
            logger.info(f"Plan submitted for review: {plan_id}")
            return review_request
            
        except Exception as e:
            logger.error(f"Failed to submit plan for review: {e}")
            raise
    
    def process_user_feedback(
        self,
        plan_id: str,
        action: str,
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ユーザーフィードバックを処理
        
        Args:
            plan_id: 計画ID
            action: アクション (approve, reject, modify)
            feedback: フィードバック内容
            
        Returns:
            処理結果
        """
        try:
            plan = self.active_plans.get(plan_id)
            if not plan:
                raise ValueError(f"Plan not found: {plan_id}")
            
            # フィードバックを記録
            feedback_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'action': action,
                'feedback': feedback
            }
            plan.user_feedback.append(feedback_entry)
            
            if action == 'approve':
                plan.status = PlanStatus.APPROVED
                result = {'status': 'approved', 'message': '計画が承認されました'}
                
            elif action == 'reject':
                plan.status = PlanStatus.REJECTED
                result = {'status': 'rejected', 'message': '計画が却下されました'}
                
            elif action == 'modify':
                # 修正依頼の処理
                modified_plan = self._apply_modifications(plan, feedback)
                modified_plan.status = PlanStatus.MODIFIED
                
                # 修正履歴を記録
                modification_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'original_steps': len(plan.steps),
                    'modified_steps': len(modified_plan.steps),
                    'changes': feedback.get('changes', [])
                }
                modified_plan.modifications.append(modification_entry)
                
                self.active_plans[plan_id] = modified_plan
                result = {
                    'status': 'modified',
                    'message': '計画が修正されました',
                    'modified_plan': modified_plan.to_dict()
                }
                
            else:
                raise ValueError(f"Invalid action: {action}")
            
            plan.updated_at = datetime.utcnow()
            self._save_plan(plan)
            
            logger.info(f"User feedback processed: {plan_id} - {action}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process user feedback: {e}")
            raise
    
    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """
        計画を取得
        
        Args:
            plan_id: 計画ID
            
        Returns:
            実行計画
        """
        return self.active_plans.get(plan_id)
    
    def list_plans(
        self,
        status: Optional[PlanStatus] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        計画一覧を取得
        
        Args:
            status: フィルターするステータス
            limit: 取得数制限
            
        Returns:
            計画一覧
        """
        plans = list(self.active_plans.values())
        
        if status:
            plans = [plan for plan in plans if plan.status == status]
        
        # 作成日時でソート（新しい順）
        plans.sort(key=lambda p: p.created_at, reverse=True)
        
        return [plan.to_dict() for plan in plans[:limit]]
    
    def _decompose_task(
        self,
        task_description: str,
        context: Dict[str, Any] = None
    ) -> List[PlanStep]:
        """
        タスクをステップに分解
        
        Args:
            task_description: タスクの説明
            context: コンテキスト情報
            
        Returns:
            ステップのリスト
        """
        # 簡単な実装：タスクの種類に基づいてテンプレートを使用
        task_lower = task_description.lower()
        
        if 'web' in task_lower and ('アプリ' in task_lower or 'サイト' in task_lower):
            return self._create_web_app_steps(task_description)
        elif 'api' in task_lower:
            return self._create_api_steps(task_description)
        elif 'データ' in task_lower or 'data' in task_lower:
            return self._create_data_analysis_steps(task_description)
        else:
            return self._create_generic_steps(task_description)
    
    def _create_web_app_steps(self, task_description: str) -> List[PlanStep]:
        """Webアプリケーション開発のステップを生成"""
        steps = [
            PlanStep(
                id="step_1",
                title="要件分析",
                description="タスクの詳細を分析し、技術要件を決定",
                type="analysis",
                estimated_time=300,  # 5分
                dependencies=[],
                tools=["qwen_engine"],
                parameters={"task": task_description},
                risk_level="low",
                reversible=True
            ),
            PlanStep(
                id="step_2",
                title="プロジェクト構造作成",
                description="Webアプリケーションのディレクトリ構造を作成",
                type="file_operation",
                estimated_time=180,  # 3分
                dependencies=["step_1"],
                tools=["file_manager"],
                parameters={"action": "create_structure"},
                risk_level="low",
                reversible=True
            ),
            PlanStep(
                id="step_3",
                title="バックエンド実装",
                description="APIエンドポイントとビジネスロジックを実装",
                type="code_generation",
                estimated_time=1200,  # 20分
                dependencies=["step_2"],
                tools=["qwen_engine", "code_executor"],
                parameters={"language": "python", "framework": "flask"},
                risk_level="medium",
                reversible=True
            ),
            PlanStep(
                id="step_4",
                title="フロントエンド実装",
                description="ユーザーインターフェースを実装",
                type="code_generation",
                estimated_time=1800,  # 30分
                dependencies=["step_2"],
                tools=["qwen_engine", "code_executor"],
                parameters={"language": "javascript", "framework": "react"},
                risk_level="medium",
                reversible=True
            ),
            PlanStep(
                id="step_5",
                title="統合テスト",
                description="フロントエンドとバックエンドの統合テスト",
                type="testing",
                estimated_time=600,  # 10分
                dependencies=["step_3", "step_4"],
                tools=["code_executor", "web_browser"],
                parameters={"test_type": "integration"},
                risk_level="low",
                reversible=True
            ),
            PlanStep(
                id="step_6",
                title="GitHubコミット",
                description="完成したコードをGitHubにコミット",
                type="git_operation",
                estimated_time=300,  # 5分
                dependencies=["step_5"],
                tools=["github_client"],
                parameters={"action": "commit_and_push"},
                risk_level="low",
                reversible=False
            )
        ]
        return steps
    
    def _create_api_steps(self, task_description: str) -> List[PlanStep]:
        """API開発のステップを生成"""
        steps = [
            PlanStep(
                id="step_1",
                title="API設計",
                description="APIエンドポイントとスキーマを設計",
                type="design",
                estimated_time=600,
                dependencies=[],
                tools=["qwen_engine"],
                parameters={"task": task_description},
                risk_level="low",
                reversible=True
            ),
            PlanStep(
                id="step_2",
                title="API実装",
                description="RESTful APIを実装",
                type="code_generation",
                estimated_time=1800,
                dependencies=["step_1"],
                tools=["qwen_engine", "code_executor"],
                parameters={"framework": "flask"},
                risk_level="medium",
                reversible=True
            ),
            PlanStep(
                id="step_3",
                title="APIテスト",
                description="APIエンドポイントのテスト",
                type="testing",
                estimated_time=900,
                dependencies=["step_2"],
                tools=["code_executor"],
                parameters={"test_type": "api"},
                risk_level="low",
                reversible=True
            )
        ]
        return steps
    
    def _create_data_analysis_steps(self, task_description: str) -> List[PlanStep]:
        """データ分析のステップを生成"""
        steps = [
            PlanStep(
                id="step_1",
                title="データ収集",
                description="必要なデータを収集・取得",
                type="data_collection",
                estimated_time=900,
                dependencies=[],
                tools=["web_browser", "api_client"],
                parameters={"task": task_description},
                risk_level="low",
                reversible=True
            ),
            PlanStep(
                id="step_2",
                title="データ前処理",
                description="データのクリーニングと前処理",
                type="data_processing",
                estimated_time=1200,
                dependencies=["step_1"],
                tools=["code_executor"],
                parameters={"language": "python"},
                risk_level="medium",
                reversible=True
            ),
            PlanStep(
                id="step_3",
                title="データ分析",
                description="統計分析と可視化",
                type="analysis",
                estimated_time=1800,
                dependencies=["step_2"],
                tools=["code_executor"],
                parameters={"analysis_type": "statistical"},
                risk_level="low",
                reversible=True
            )
        ]
        return steps
    
    def _create_generic_steps(self, task_description: str) -> List[PlanStep]:
        """汎用的なステップを生成"""
        steps = [
            PlanStep(
                id="step_1",
                title="タスク分析",
                description="タスクの詳細を分析",
                type="analysis",
                estimated_time=300,
                dependencies=[],
                tools=["qwen_engine"],
                parameters={"task": task_description},
                risk_level="low",
                reversible=True
            ),
            PlanStep(
                id="step_2",
                title="実装",
                description="タスクを実装",
                type="implementation",
                estimated_time=1200,
                dependencies=["step_1"],
                tools=["qwen_engine", "code_executor"],
                parameters={"task": task_description},
                risk_level="medium",
                reversible=True
            ),
            PlanStep(
                id="step_3",
                title="検証",
                description="実装結果を検証",
                type="verification",
                estimated_time=600,
                dependencies=["step_2"],
                tools=["code_executor"],
                parameters={"verification_type": "basic"},
                risk_level="low",
                reversible=True
            )
        ]
        return steps
    
    def _assess_risks(self, steps: List[PlanStep]) -> Dict[str, Any]:
        """リスク評価を実行"""
        high_risk_count = sum(1 for step in steps if step.risk_level == "high")
        medium_risk_count = sum(1 for step in steps if step.risk_level == "medium")
        irreversible_count = sum(1 for step in steps if not step.reversible)
        
        # 全体的なリスクレベルを決定
        if high_risk_count > 0 or irreversible_count > 2:
            overall_risk = "high"
        elif medium_risk_count > len(steps) // 2:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        return {
            'overall_risk': overall_risk,
            'high_risk_steps': high_risk_count,
            'medium_risk_steps': medium_risk_count,
            'irreversible_steps': irreversible_count,
            'total_steps': len(steps),
            'risk_factors': self._identify_risk_factors(steps)
        }
    
    def _identify_risk_factors(self, steps: List[PlanStep]) -> List[str]:
        """リスク要因を特定"""
        risk_factors = []
        
        for step in steps:
            if not step.reversible:
                risk_factors.append(f"不可逆操作: {step.title}")
            if step.risk_level == "high":
                risk_factors.append(f"高リスク操作: {step.title}")
            if "git" in step.type.lower() or "github" in step.tools:
                risk_factors.append(f"外部リポジトリ操作: {step.title}")
        
        return risk_factors
    
    def _generate_plan_title(self, task_description: str) -> str:
        """計画タイトルを生成"""
        # 簡単な実装：タスクの最初の50文字を使用
        title = task_description[:50]
        if len(task_description) > 50:
            title += "..."
        return title
    
    def _generate_steps_summary(self, steps: List[PlanStep]) -> List[Dict[str, Any]]:
        """ステップの要約を生成"""
        return [
            {
                'id': step.id,
                'title': step.title,
                'description': step.description,
                'estimated_time': step.estimated_time,
                'risk_level': step.risk_level,
                'reversible': step.reversible
            }
            for step in steps
        ]
    
    def _get_high_risk_steps(self, steps: List[PlanStep]) -> List[Dict[str, Any]]:
        """高リスクステップを取得"""
        return [
            {'id': step.id, 'title': step.title, 'description': step.description}
            for step in steps if step.risk_level == "high"
        ]
    
    def _get_irreversible_steps(self, steps: List[PlanStep]) -> List[Dict[str, Any]]:
        """不可逆ステップを取得"""
        return [
            {'id': step.id, 'title': step.title, 'description': step.description}
            for step in steps if not step.reversible
        ]
    
    def _apply_modifications(
        self,
        plan: ExecutionPlan,
        feedback: Dict[str, Any]
    ) -> ExecutionPlan:
        """修正依頼を適用"""
        # 新しい計画を作成
        modified_plan = ExecutionPlan(
            plan_id=plan.plan_id,
            title=plan.title,
            description=plan.description,
            steps=plan.steps.copy(),
            estimated_total_time=plan.estimated_total_time,
            risk_assessment=plan.risk_assessment.copy()
        )
        
        # 修正内容を適用
        changes = feedback.get('changes', [])
        
        for change in changes:
            change_type = change.get('type', '')
            
            if change_type == 'remove_step':
                step_id = change.get('step_id', '')
                modified_plan.steps = [s for s in modified_plan.steps if s.id != step_id]
                
            elif change_type == 'modify_step':
                step_id = change.get('step_id', '')
                modifications = change.get('modifications', {})
                
                for step in modified_plan.steps:
                    if step.id == step_id:
                        for key, value in modifications.items():
                            if hasattr(step, key):
                                setattr(step, key, value)
                        break
                        
            elif change_type == 'add_step':
                new_step_data = change.get('step_data', {})
                new_step = PlanStep(**new_step_data)
                modified_plan.steps.append(new_step)
        
        # 推定時間を再計算
        modified_plan.estimated_total_time = sum(step.estimated_time for step in modified_plan.steps)
        
        # リスク評価を再実行
        modified_plan.risk_assessment = self._assess_risks(modified_plan.steps)
        
        return modified_plan
    
    def _save_plan(self, plan: ExecutionPlan):
        """計画をファイルに保存"""
        try:
            file_path = os.path.join(self.storage_dir, f"{plan.plan_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plan {plan.plan_id}: {e}")
    
    def _load_plan_templates(self) -> Dict[str, Any]:
        """計画テンプレートを読み込み"""
        # 簡単な実装：空の辞書を返す
        return {}

# 使用例とテスト関数
def test_plan_reviewer():
    """PlanReviewerのテスト"""
    try:
        plan_reviewer = PlanReviewer()
        
        # テスト計画の作成
        print("=== 計画作成テスト ===")
        plan = plan_reviewer.create_plan("Webアプリケーションを作成してください")
        print(f"Plan created: {plan.plan_id}")
        print(f"Steps: {len(plan.steps)}")
        print(f"Estimated time: {plan.estimated_total_time} seconds")
        print(f"Risk level: {plan.risk_assessment['overall_risk']}")
        
        # レビュー依頼
        print("\n=== レビュー依頼テスト ===")
        review_request = plan_reviewer.submit_for_review(plan.plan_id)
        print(f"Review request: {review_request['title']}")
        print(f"High risk steps: {len(review_request['high_risk_steps'])}")
        
        # ユーザーフィードバック（承認）
        print("\n=== フィードバック処理テスト ===")
        result = plan_reviewer.process_user_feedback(
            plan.plan_id,
            'approve',
            {'comment': 'Good plan!'}
        )
        print(f"Feedback result: {result['status']}")
        
        # 計画一覧
        print("\n=== 計画一覧テスト ===")
        plans = plan_reviewer.list_plans()
        print(f"Total plans: {len(plans)}")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_plan_reviewer()

