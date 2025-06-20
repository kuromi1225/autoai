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
        
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """タスクを処理する"""
        try:
            # タスクステータスを更新
            task.status = 'planning'
            task.started_at = datetime.utcnow()
            db.session.commit()
            
            # 計画を生成
            plan = await self.generate_plan(task)
            
            # 計画を実行
            execution = await self.execute_plan(task, plan)
            
            # 結果を返す
            return {
                'task_id': task.id,
                'status': 'completed',
                'plan': plan.to_dict(),
                'execution': execution.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            task.status = 'failed'
            db.session.commit()
            raise
    
    async def generate_plan(self, task: Task) -> Plan:
        """タスクの実行計画を生成する"""
        
        # プロンプトを構築
        prompt = self._build_planning_prompt(task)
        
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
    
    def _build_planning_prompt(self, task: Task) -> str:
        """計画生成用のプロンプトを構築する"""
        
        available_tools = self.tool_manager.get_available_tools()
        
        prompt = f"""
あなたは汎用自律型AIエージェントです。以下のタスクを実行するための詳細な計画を作成してください。

タスク情報:
- タイトル: {task.title}
- 説明: {task.description}
- 優先度: {task.priority}

利用可能なツール:
{json.dumps(available_tools, indent=2, ensure_ascii=False)}

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
    
    async def add_task(self, task: Task) -> str:
        """タスクをキューに追加する"""
        
        # タスクを非同期で実行
        task_future = asyncio.create_task(self.agent.process_task(task))
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

