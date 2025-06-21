# API エンドポイント定義

from flask import request, jsonify
from flask_socketio import emit
from datetime import datetime
import asyncio
import json
from models import db, Task, Plan, Execution, ExecutionLog, Session, Message
from ai_agent import AIAgent, TaskQueue
from services.auth_service import require_auth, get_current_user

# グローバル変数
ai_agent = None
task_queue = None

def init_ai_system(app):
    """AI システムを初期化する"""
    global ai_agent, task_queue
    
    openai_api_key = app.config.get('OPENAI_API_KEY')
    if not openai_api_key:
        app.logger.warning("OPENAI_API_KEY not configured")
        return
    
    ai_agent = AIAgent(openai_api_key)
    task_queue = TaskQueue(ai_agent)
    app.logger.info("AI system initialized")

def register_api_routes(app, socketio):
    """API ルートを登録する"""
    
    @app.route('/api/tasks', methods=['POST'])
    @require_auth
    def create_task():
        """新しいタスクを作成する"""
        try:
            user = get_current_user()
            data = request.get_json()
            
            # バリデーション
            if not data.get('title') or not data.get('description'):
                return jsonify({'error': 'Title and description are required'}), 400
            
            # タスクを作成
            task = Task(
                user_id=user.id,
                title=data['title'],
                description=data['description'],
                priority=data.get('priority', 'medium'),
                metadata=data.get('metadata', {})
            )
            
            db.session.add(task)
            db.session.commit()
            
            # repo_url を取得
            repo_url = data.get('repo_url')

            # タスクをキューに追加
            if task_queue:
                asyncio.create_task(task_queue.add_task(task, repo_url)) # repo_url を渡す
            
            return jsonify({
                'success': True,
                'task': task.to_dict()
            }), 201
            
        except Exception as e:
            app.logger.error(f"Task creation failed: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/tasks', methods=['GET'])
    @require_auth
    def get_tasks():
        """ユーザーのタスク一覧を取得する"""
        try:
            user = get_current_user()
            
            # クエリパラメータ
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            # クエリを構築
            query = Task.query.filter_by(user_id=user.id)
            
            if status:
                query = query.filter_by(status=status)
            
            query = query.order_by(Task.created_at.desc())
            query = query.offset(offset).limit(limit)
            
            tasks = query.all()
            
            return jsonify({
                'success': True,
                'tasks': [task.to_dict() for task in tasks]
            })
            
        except Exception as e:
            app.logger.error(f"Failed to get tasks: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/tasks/<task_id>', methods=['GET'])
    @require_auth
    def get_task(task_id):
        """特定のタスクを取得する"""
        try:
            user = get_current_user()
            
            task = Task.query.filter_by(id=task_id, user_id=user.id).first()
            if not task:
                return jsonify({'error': 'Task not found'}), 404
            
            # 関連データも含める
            task_data = task.to_dict()
            task_data['plans'] = [plan.to_dict() for plan in task.plans]
            task_data['executions'] = [execution.to_dict() for execution in task.executions]
            
            return jsonify({
                'success': True,
                'task': task_data
            })
            
        except Exception as e:
            app.logger.error(f"Failed to get task: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/tasks/<task_id>/status', methods=['GET'])
    @require_auth
    def get_task_status(task_id):
        """タスクの実行状況を取得する"""
        try:
            user = get_current_user()
            
            task = Task.query.filter_by(id=task_id, user_id=user.id).first()
            if not task:
                return jsonify({'error': 'Task not found'}), 404
            
            # 実行状況を取得
            if task_queue:
                status = asyncio.run(task_queue.get_task_status(task_id))
            else:
                status = {
                    'task_id': task_id,
                    'status': task.status,
                    'message': 'AI system not available'
                }
            
            return jsonify({
                'success': True,
                'status': status
            })
            
        except Exception as e:
            app.logger.error(f"Failed to get task status: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
    @require_auth
    def cancel_task(task_id):
        """タスクをキャンセルする"""
        try:
            user = get_current_user()
            
            task = Task.query.filter_by(id=task_id, user_id=user.id).first()
            if not task:
                return jsonify({'error': 'Task not found'}), 404
            
            # タスクをキャンセル
            if task_queue:
                cancelled = asyncio.run(task_queue.cancel_task(task_id))
            else:
                task.status = 'cancelled'
                db.session.commit()
                cancelled = True
            
            return jsonify({
                'success': True,
                'cancelled': cancelled
            })
            
        except Exception as e:
            app.logger.error(f"Failed to cancel task: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/executions/<execution_id>/logs', methods=['GET'])
    @require_auth
    def get_execution_logs(execution_id):
        """実行ログを取得する"""
        try:
            user = get_current_user()
            
            # 実行レコードを取得
            execution = Execution.query.join(Task).filter(
                Execution.id == execution_id,
                Task.user_id == user.id
            ).first()
            
            if not execution:
                return jsonify({'error': 'Execution not found'}), 404
            
            # ログを取得
            logs = ExecutionLog.query.filter_by(execution_id=execution_id).order_by(
                ExecutionLog.step_number, ExecutionLog.timestamp
            ).all()
            
            return jsonify({
                'success': True,
                'logs': [log.to_dict() for log in logs]
            })
            
        except Exception as e:
            app.logger.error(f"Failed to get execution logs: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/sessions', methods=['POST'])
    @require_auth
    def create_session():
        """新しいセッションを作成する"""
        try:
            user = get_current_user()
            data = request.get_json()
            
            session = Session(
                user_id=user.id,
                name=data.get('name', f'Session {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}'),
                description=data.get('description', ''),
                context=data.get('context', {}),
                settings=data.get('settings', {})
            )
            
            db.session.add(session)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'session': session.to_dict()
            }), 201
            
        except Exception as e:
            app.logger.error(f"Session creation failed: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/sessions', methods=['GET'])
    @require_auth
    def get_sessions():
        """ユーザーのセッション一覧を取得する"""
        try:
            user = get_current_user()
            
            sessions = Session.query.filter_by(user_id=user.id).order_by(
                Session.updated_at.desc()
            ).all()
            
            return jsonify({
                'success': True,
                'sessions': [session.to_dict() for session in sessions]
            })
            
        except Exception as e:
            app.logger.error(f"Failed to get sessions: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/sessions/<session_id>/messages', methods=['POST'])
    @require_auth
    def add_message(session_id):
        """セッションにメッセージを追加する"""
        try:
            user = get_current_user()
            data = request.get_json()
            
            # セッションの存在確認
            session = Session.query.filter_by(id=session_id, user_id=user.id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            # メッセージを作成
            message = Message(
                session_id=session_id,
                role=data.get('role', 'user'),
                content=data['content'],
                metadata=data.get('metadata', {})
            )
            
            db.session.add(message)
            
            # セッションの更新日時を更新
            session.updated_at = datetime.utcnow()
            db.session.commit()
            
            # WebSocketで通知
            socketio.emit('new_message', {
                'session_id': session_id,
                'message': message.to_dict()
            }, room=f'user_{user.id}')
            
            return jsonify({
                'success': True,
                'message': message.to_dict()
            }), 201
            
        except Exception as e:
            app.logger.error(f"Failed to add message: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/sessions/<session_id>/messages', methods=['GET'])
    @require_auth
    def get_messages(session_id):
        """セッションのメッセージを取得する"""
        try:
            user = get_current_user()
            
            # セッションの存在確認
            session = Session.query.filter_by(id=session_id, user_id=user.id).first()
            if not session:
                return jsonify({'error': 'Session not found'}), 404
            
            # メッセージを取得
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
            
            messages = Message.query.filter_by(session_id=session_id).order_by(
                Message.timestamp.asc()
            ).offset(offset).limit(limit).all()
            
            return jsonify({
                'success': True,
                'messages': [message.to_dict() for message in messages]
            })
            
        except Exception as e:
            app.logger.error(f"Failed to get messages: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/tools', methods=['GET'])
    @require_auth
    def get_available_tools():
        """利用可能なツール一覧を取得する"""
        try:
            if ai_agent:
                tools = ai_agent.tool_manager.get_available_tools()
            else:
                tools = []
            
            return jsonify({
                'success': True,
                'tools': tools
            })
            
        except Exception as e:
            app.logger.error(f"Failed to get tools: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # WebSocket イベント
    @socketio.on('connect')
    @require_auth
    def handle_connect():
        """WebSocket接続時の処理"""
        user = get_current_user()
        if user:
            # ユーザー専用のルームに参加
            socketio.join_room(f'user_{user.id}')
            emit('connected', {'message': 'Connected to AI Agent'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """WebSocket切断時の処理"""
        pass
    
    @socketio.on('task_update')
    @require_auth
    def handle_task_update(data):
        """タスク更新の通知"""
        user = get_current_user()
        if user:
            # タスクの実行状況を取得して送信
            task_id = data.get('task_id')
            if task_id and task_queue:
                try:
                    status = asyncio.run(task_queue.get_task_status(task_id))
                    emit('task_status', status)
                except Exception as e:
                    emit('error', {'message': str(e)})

