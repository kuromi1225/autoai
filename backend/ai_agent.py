# AIエージェント実行エンジン

import openai
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from models import db, Task, Plan, Execution, ExecutionLog
from tools.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class AIAgent:
    """汎用自律型AIエージェント"""
    
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.tool_manager = ToolManager()
        
    async def process_task(self, task: Task, repo_url: Optional[str] = None) -> Dict[str, Any]:
        """タスクを処理する"""
        # WebSocketやログを通じてステータスを更新するヘルパー関数を想定
        def _update_status(message: str, new_status: Optional[str] = None):
            logger.info(f"[Task {task.id}] {message}")
            if new_status:
                task.status = new_status
                db.session.commit()
            # ここでWebSocket経由でフロントエンドに通知する処理を追加
            # socketio.emit('task_update', {'task_id': task.id, 'status': new_status, 'message': message}, room=f'user_{task.user_id}')

        try:
            _update_status(f"タスク '{task.title}' を開始します。", 'running')
            task.started_at = datetime.utcnow()
            db.session.commit()

            # 1. リポジトリのクローン (repo_urlが指定されている場合)
            if repo_url:
                _update_status(f"リポジトリ {repo_url} をクローン中...")
                # ToolManager経由でgitツールを呼び出す
                clone_params = {'action': 'clone', 'repo_url': repo_url, 'directory': '.'}
                clone_result = await self.tool_manager.execute_tool('git', clone_params)
                _update_status(clone_result.get('message', 'Clone attempt finished.'))
                if not clone_result.get('success'):
                    raise Exception(f"リポジトリのクローンに失敗しました: {clone_result.get('error', 'Unknown error')}")
            else:
                _update_status("リポジトリURLが指定されていないため、クローン処理をスキップします。")

            # 2. 計画立案
            _update_status("PMが既存コードを分析し、計画を作成中...", 'planning')
            # generate_plan内で現在のワークスペースの情報をプロンプトに含めるように修正が必要
            plan = await self.generate_plan(task, repo_url is not None) # repo_urlの有無を渡す
            _update_status(f"計画 '{plan.title}' が作成されました。実行に移ります。", 'executing_plan')

            # 3. タスク実行ループ
            execution = await self.execute_plan(task, plan)
            if execution.status == 'failed':
                raise Exception(f"計画の実行に失敗しました: {execution.error_info}")

            _update_status("計画の全ステップが完了しました。")

            # 4. 全タスク完了後のコミットメッセージ生成＆コミット＆プッシュ (repo_urlが指定されていた場合)
            if repo_url:
                _update_status("コミットメッセージを生成中...")
                # ここでは簡単のため、タスクタイトルとゴールを元にメッセージを生成
                # 本来はPMエージェントに専用のプロンプトで生成させる
                commit_message_prompt = f"Goal: {task.description}\nAll tasks for the goal '{task.title}' are complete. Please generate a concise and informative commit message."
                generated_commit_message = await self._call_openai(commit_message_prompt, "commit_message_generation")
                # OpenAIのレスポンスからメッセージ部分を抽出する必要があるかもしれない
                commit_message = generated_commit_message.strip()
                if not commit_message: # 空の場合のフォールバック
                    commit_message = f"Completed task: {task.title}"


                _update_status(f"変更をコミット中...\nMessage: {commit_message}")
                commit_params = {'action': 'commit', 'message': commit_message}
                commit_result = await self.tool_manager.execute_tool('git', commit_params)
                _update_status(commit_result.get('message', 'Commit attempt finished.'))
                if not commit_result.get('success'):
                    # コミット失敗時はプッシュをスキップするが、エラーは記録
                    logger.error(f"コミットに失敗しました: {commit_result.get('error', 'Unknown error')}")
                else:
                    _update_status("リモートリポジトリにプッシュ中...")
                    push_params = {'action': 'push'}
                    push_result = await self.tool_manager.execute_tool('git', push_params)
                    _update_status(push_result.get('message', 'Push attempt finished.'))
                    if not push_result.get('success'):
                         logger.error(f"プッシュに失敗しました: {push_result.get('error', 'Unknown error')}")


            # 5. 最終完了報告
            final_message = f"タスク '{task.title}' が正常に完了しました。"
            if repo_url:
                final_message += " 変更はリポジトリにプッシュされました（試行されました）。"
            _update_status(final_message, 'completed')
            task.completed_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'task_id': task.id,
                'status': 'completed',
                'message': final_message,
                'plan': plan.to_dict(),
                'execution': execution.to_dict()
            }
            
        except Exception as e:
            error_message = f"タスク処理中にエラーが発生しました: {e}"
            logger.error(f"[Task {task.id}] {error_message}")
            _update_status(error_message, 'failed')
            task.error_info = {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}
            db.session.commit()
            # エラー情報を返すか、あるいは呼び出し元で適切に処理する
            return {
                'task_id': task.id,
                'status': 'failed',
                'error': error_message
            }

    async def generate_plan(self, task: Task, has_cloned_repo: bool) -> Plan:
        """
        タスクの実行計画を生成する
        has_cloned_repo: リポジトリがクローンされている場合True
        """
        
        # プロンプトを構築
        prompt = self._build_planning_prompt(task, has_cloned_repo) # has_cloned_repo を渡す
        
        # OpenAI APIを呼び出し
        response = await self._call_openai(prompt, "plan_generation")
        
        # レスポンスを解析
        plan_data = self._parse_plan_response(response)
        
        # データベースに保存
        plan = Plan(
            task_id=task.id,
            title=plan_data['title'],
            description=plan_data['description'],
            steps=plan_data['steps'],
            estimated_duration=plan_data.get('estimated_duration'),
            required_tools=plan_data.get('required_tools', []),
            status='approved'
        )
        
        db.session.add(plan)
        db.session.commit()
        
        return plan
    
    async def execute_plan(self, task: Task, plan: Plan) -> Execution:
        """計画を実行する"""
        
        # 実行レコードを作成
        execution = Execution(
            task_id=task.id,
            plan_id=plan.id,
            total_steps=len(plan.steps),
            status='running'
        )
        
        db.session.add(execution)
        db.session.commit()
        
        try:
            # ステップを順次実行
            for i, step in enumerate(plan.steps):
                execution.current_step = i + 1
                db.session.commit()
                
                # ステップを実行
                step_result = await self.execute_step(execution, step, i + 1)
                
                # ログを記録
                self._log_step_result(execution, step, step_result, i + 1)
            
            # 実行完了
            execution.status = 'completed'
            execution.completed_at = datetime.utcnow()
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            
        except Exception as e:
            # 実行失敗
            execution.status = 'failed'
            execution.error_info = {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}
            task.status = 'failed'
            logger.error(f"Plan execution failed: {e}")
            
        db.session.commit()
        return execution
    
    async def execute_step(self, execution: Execution, step: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """個別ステップを実行する"""
        
        step_type = step.get('type')
        step_params = step.get('parameters', {})
        
        # ツールを使用してステップを実行
        if step_type in ['browser', 'file', 'code', 'api']:
            return await self.tool_manager.execute_tool(step_type, step_params)
        
        # AIによる推論ステップ
        elif step_type == 'reasoning':
            return await self._execute_reasoning_step(step_params)
        
        # その他のステップタイプ
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    async def _execute_reasoning_step(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """推論ステップを実行する"""
        
        prompt = params.get('prompt', '')
        context = params.get('context', {})
        
        # OpenAI APIを呼び出し
        response = await self._call_openai(prompt, "reasoning", context)
        
        return {
            'type': 'reasoning',
            'result': response,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _build_planning_prompt(self, task: Task, has_cloned_repo: bool) -> str:
        """計画生成用のプロンプトを構築する"""
        
        available_tools = self.tool_manager.get_available_tools()
        
        repo_analysis_prompt = ""
        if has_cloned_repo:
            repo_analysis_prompt = """
**重要: リポジトリ分析**
- 現在のワークスペースには、指定されたGitリポジトリがクローンされています。
- 計画の初期段階で、`list_files` や `read_file` ツールを使用して既存のコードベースを十分に調査し、タスクに関連するファイル構造、既存のコード、設計パターンを理解してください。
- この分析結果を計画の設計フェーズに活かしてください。
"""

        prompt = f"""
あなたはプロジェクトマネージャー、設計者、プログラマー、テスターの能力を兼ね備えた高度な自律型AIエージェントです。
以下のタスクを実行するための詳細な計画を作成し、最終的にはコミットメッセージも生成できるように準備してください。

**エージェントとしての能力:**
*   **プロジェクト管理:** 既存のコードベースを分析し、変更による影響範囲を予測し、タスク全体を管理します。最終的なコミットメッセージの案も作成します。
*   **設計:** Git管理下の既存コードを読み解き、整合性を保った設計を行います。ファイル構造や既存の設計パターンを考慮します。
*   **プログラミング:** 設計に基づき、既存のコードを読み、修正または新規にコードを書き込みます。品質と保守性を重視します。
*   **テスト:** 作成・修正したコードの単体テスト、結合テストを実施します。変更箇所だけでなく、影響が考えられる範囲のリグレッションテストも考慮します。

**タスク情報:**
- タイトル: {task.title}
- 説明: {task.description}
- 優先度: {task.priority}
- (必要であればリポジトリのURLやブランチ名などの情報もここに追加できます)
{repo_analysis_prompt}
**利用可能なツール:**
{json.dumps(available_tools, indent=2, ensure_ascii=False)}

**計画作成の指示:**
1.  **リポジトリ分析フェーズ (必要な場合):** { "既存コードの理解を深めるために、`git clone` (未実施の場合) や `file list/read` ツールを使った分析ステップを計画に含めてください。" if not has_cloned_repo else "（リポジトリはクローン済みです。上記「重要: リポジトリ分析」の指示に従ってください。）"}
2.  **段階的な実装:** 設計、実装、テストの各フェーズを明確に区別し、それぞれのステップで何を行うかを具体的に記述してください。
3.  **ツール活用:** 利用可能なツールを効果的に使用するステップを計画に含めてください。特に、ファイル操作、コード実行、Git操作（コミットは計画の最後、または別途指示）を意識してください。
4.  **リグレッションテスト:** 変更による影響範囲を考慮し、関連する機能のテストも計画に含めてください。

**出力形式 (JSON):**
以下のJSON形式で計画を返してください:
{{
    "title": "計画のタイトル",
    "description": "計画の詳細説明",
    "estimated_duration": 推定実行時間（分）,
    "required_tools": ["必要なツールのリスト"],
    "steps": [
        {{
            "id": 1,
            "title": "ステップのタイトル",
            "description": "ステップの説明",
            "type": "ステップタイプ（browser/file/code/api/reasoning）",
            "parameters": {{
                "パラメータ名": "値"
            }},
            "expected_output": "期待される出力",
            "dependencies": ["依存するステップのID"]
        }}
    ]
}}

計画は具体的で実行可能なステップに分解してください。
各ステップは明確な目的と期待される結果を持つ必要があります。
"""
        
        return prompt
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """計画生成レスポンスを解析する"""
        
        try:
            # JSONを抽出
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            
            plan_data = json.loads(json_str)
            
            # 必須フィールドの検証
            required_fields = ['title', 'description', 'steps']
            for field in required_fields:
                if field not in plan_data:
                    raise ValueError(f"Missing required field: {field}")
            
            return plan_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse plan response: {e}")
            raise ValueError(f"Invalid plan format: {e}")
    
    async def _call_openai(self, prompt: str, task_type: str, context: Dict[str, Any] = None) -> str:
        """OpenAI APIを呼び出す"""
        
        messages = [
            {
                "role": "system",
                "content": "あなたは汎用自律型AIエージェントです。与えられたタスクを正確に実行してください。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # コンテキストがある場合は追加
        if context:
            messages.insert(-1, {
                "role": "assistant",
                "content": f"コンテキスト: {json.dumps(context, ensure_ascii=False)}"
            })
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _log_step_result(self, execution: Execution, step: Dict[str, Any], result: Dict[str, Any], step_number: int):
        """ステップ実行結果をログに記録する"""
        
        log_entry = ExecutionLog(
            execution_id=execution.id,
            step_number=step_number,
            log_level='INFO',
            message=f"Step {step_number} completed: {step.get('title', 'Unknown')}",
            metadata={
                'step': step,
                'result': result
            }
        )
        
        db.session.add(log_entry)
        db.session.commit()

class TaskQueue:
    """タスクキュー管理"""
    
    def __init__(self, agent: AIAgent):
        self.agent = agent
        self.running_tasks = {}
    
    async def add_task(self, task: Task, repo_url: Optional[str] = None) -> str:
        """タスクをキューに追加する"""
        
        # タスクを非同期で実行
        task_future = asyncio.create_task(self.agent.process_task(task, repo_url)) # repo_url を渡す
        self.running_tasks[task.id] = task_future
        
        return task.id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """タスクの実行状況を取得する"""
        
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # 実行中のタスクの場合
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            
            if future.done():
                # 完了した場合は結果を取得
                try:
                    result = await future
                    del self.running_tasks[task_id]
                    return result
                except Exception as e:
                    del self.running_tasks[task_id]
                    return {
                        'task_id': task_id,
                        'status': 'failed',
                        'error': str(e)
                    }
            else:
                # まだ実行中
                return {
                    'task_id': task_id,
                    'status': task.status,
                    'message': 'Task is running'
                }
        
        # 完了済みタスクの場合
        return {
            'task_id': task_id,
            'status': task.status,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """タスクをキャンセルする"""
        
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            future.cancel()
            del self.running_tasks[task_id]
            
            # データベースを更新
            task = Task.query.get(task_id)
            if task:
                task.status = 'cancelled'
                db.session.commit()
            
            return True
        
        return False

