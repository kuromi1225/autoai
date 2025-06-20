"""
WebSocket通信とリアルタイムストリーミング

このモジュールは、フロントエンドとバックエンド間のリアルタイム通信を
WebSocketを使用して実装します。
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import uuid

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import redis

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket接続とメッセージングを管理"""
    
    def __init__(self, socketio: SocketIO, redis_client: redis.Redis):
        self.socketio = socketio
        self.redis_client = redis_client
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self.session_rooms: Dict[str, str] = {}  # session_id -> room_id
        
        # イベントハンドラーを登録
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """WebSocketイベントハンドラーを登録"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """クライアント接続時の処理"""
            session_id = request.sid
            user_id = auth.get('user_id') if auth else None
            
            logger.info(f"WebSocket connected: {session_id}, user: {user_id}")
            
            # 接続情報を記録
            self.active_connections[session_id] = {
                'user_id': user_id,
                'connected_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
            
            if user_id:
                if user_id not in self.user_sessions:
                    self.user_sessions[user_id] = []
                self.user_sessions[user_id].append(session_id)
                
                # ユーザー専用ルームに参加
                room_id = f"user_{user_id}"
                join_room(room_id)
                self.session_rooms[session_id] = room_id
            
            # 接続確認メッセージを送信
            emit('connection_established', {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'message': 'WebSocket connection established'
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """クライアント切断時の処理"""
            session_id = request.sid
            
            logger.info(f"WebSocket disconnected: {session_id}")
            
            # 接続情報をクリーンアップ
            if session_id in self.active_connections:
                user_id = self.active_connections[session_id].get('user_id')
                del self.active_connections[session_id]
                
                if user_id and user_id in self.user_sessions:
                    if session_id in self.user_sessions[user_id]:
                        self.user_sessions[user_id].remove(session_id)
                    if not self.user_sessions[user_id]:
                        del self.user_sessions[user_id]
            
            if session_id in self.session_rooms:
                del self.session_rooms[session_id]
        
        @self.socketio.on('join_execution_room')
        def handle_join_execution_room(data):
            """実行セッション専用ルームに参加"""
            execution_id = data.get('execution_id')
            if execution_id:
                room_id = f"execution_{execution_id}"
                join_room(room_id)
                emit('joined_execution_room', {
                    'execution_id': execution_id,
                    'room_id': room_id
                })
        
        @self.socketio.on('leave_execution_room')
        def handle_leave_execution_room(data):
            """実行セッション専用ルームから退出"""
            execution_id = data.get('execution_id')
            if execution_id:
                room_id = f"execution_{execution_id}"
                leave_room(room_id)
                emit('left_execution_room', {
                    'execution_id': execution_id,
                    'room_id': room_id
                })
        
        @self.socketio.on('ping')
        def handle_ping():
            """Pingメッセージの処理"""
            session_id = request.sid
            if session_id in self.active_connections:
                self.active_connections[session_id]['last_activity'] = datetime.now().isoformat()
            emit('pong', {'timestamp': datetime.now().isoformat()})
    
    def send_to_user(self, user_id: str, event: str, data: Dict[str, Any]):
        """特定のユーザーにメッセージを送信"""
        room_id = f"user_{user_id}"
        self.socketio.emit(event, data, room=room_id)
        logger.info(f"Message sent to user {user_id}: {event}")
    
    def send_to_execution_room(self, execution_id: str, event: str, data: Dict[str, Any]):
        """実行セッション専用ルームにメッセージを送信"""
        room_id = f"execution_{execution_id}"
        self.socketio.emit(event, data, room=room_id)
        logger.info(f"Message sent to execution room {execution_id}: {event}")
    
    def broadcast(self, event: str, data: Dict[str, Any]):
        """全ての接続されたクライアントにメッセージを送信"""
        self.socketio.emit(event, data)
        logger.info(f"Broadcast message: {event}")
    
    def get_active_connections(self) -> Dict[str, Any]:
        """アクティブな接続情報を取得"""
        return {
            'total_connections': len(self.active_connections),
            'connections': self.active_connections,
            'user_sessions': self.user_sessions
        }

class StreamingManager:
    """ストリーミング処理を管理"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.active_streams: Dict[str, Dict[str, Any]] = {}
    
    async def start_execution_stream(self, execution_id: str, user_id: str) -> str:
        """実行ストリームを開始"""
        stream_id = str(uuid.uuid4())
        
        self.active_streams[stream_id] = {
            'execution_id': execution_id,
            'user_id': user_id,
            'started_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        # ストリーム開始を通知
        self.websocket_manager.send_to_user(user_id, 'stream_started', {
            'stream_id': stream_id,
            'execution_id': execution_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return stream_id
    
    async def stream_execution_progress(self, execution_id: str, progress_data: Dict[str, Any]):
        """実行進捗をストリーミング"""
        # 実行ルームに進捗を送信
        self.websocket_manager.send_to_execution_room(execution_id, 'execution_progress', {
            'execution_id': execution_id,
            'progress': progress_data,
            'timestamp': datetime.now().isoformat()
        })
    
    async def stream_execution_log(self, execution_id: str, log_entry: Dict[str, Any]):
        """実行ログをストリーミング"""
        # 実行ルームにログを送信
        self.websocket_manager.send_to_execution_room(execution_id, 'execution_log', {
            'execution_id': execution_id,
            'log': log_entry,
            'timestamp': datetime.now().isoformat()
        })
    
    async def stream_tool_output(self, execution_id: str, tool_name: str, output: Dict[str, Any]):
        """ツール出力をストリーミング"""
        # 実行ルームにツール出力を送信
        self.websocket_manager.send_to_execution_room(execution_id, 'tool_output', {
            'execution_id': execution_id,
            'tool_name': tool_name,
            'output': output,
            'timestamp': datetime.now().isoformat()
        })
    
    async def stream_chat_response(self, user_id: str, response_chunk: str, is_final: bool = False):
        """チャット応答をストリーミング"""
        self.websocket_manager.send_to_user(user_id, 'chat_response_chunk', {
            'chunk': response_chunk,
            'is_final': is_final,
            'timestamp': datetime.now().isoformat()
        })
    
    async def end_execution_stream(self, execution_id: str, final_result: Dict[str, Any]):
        """実行ストリームを終了"""
        # 該当するストリームを検索
        stream_to_end = None
        for stream_id, stream_info in self.active_streams.items():
            if stream_info['execution_id'] == execution_id:
                stream_to_end = stream_id
                break
        
        if stream_to_end:
            self.active_streams[stream_to_end]['status'] = 'completed'
            self.active_streams[stream_to_end]['ended_at'] = datetime.now().isoformat()
            
            # ストリーム終了を通知
            self.websocket_manager.send_to_execution_room(execution_id, 'stream_ended', {
                'execution_id': execution_id,
                'final_result': final_result,
                'timestamp': datetime.now().isoformat()
            })
    
    def get_active_streams(self) -> Dict[str, Any]:
        """アクティブなストリーム情報を取得"""
        return {
            'total_streams': len(self.active_streams),
            'streams': self.active_streams
        }

class ProgressTracker:
    """進捗追跡とリアルタイム更新"""
    
    def __init__(self, streaming_manager: StreamingManager):
        self.streaming_manager = streaming_manager
        self.execution_progress: Dict[str, Dict[str, Any]] = {}
    
    async def start_tracking(self, execution_id: str, total_tasks: int):
        """進捗追跡を開始"""
        self.execution_progress[execution_id] = {
            'total_tasks': total_tasks,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'current_task': None,
            'progress_percentage': 0.0,
            'started_at': datetime.now().isoformat(),
            'estimated_completion': None
        }
        
        await self.streaming_manager.stream_execution_progress(execution_id, {
            'type': 'tracking_started',
            'total_tasks': total_tasks,
            'progress_percentage': 0.0
        })
    
    async def update_task_progress(self, execution_id: str, task_id: str, status: str, progress: float = 0.0):
        """タスクの進捗を更新"""
        if execution_id not in self.execution_progress:
            return
        
        progress_info = self.execution_progress[execution_id]
        progress_info['current_task'] = task_id
        
        if status == 'completed':
            progress_info['completed_tasks'] += 1
        elif status == 'failed':
            progress_info['failed_tasks'] += 1
        
        # 全体の進捗率を計算
        total_processed = progress_info['completed_tasks'] + progress_info['failed_tasks']
        progress_info['progress_percentage'] = (total_processed / progress_info['total_tasks']) * 100
        
        await self.streaming_manager.stream_execution_progress(execution_id, {
            'type': 'task_progress',
            'task_id': task_id,
            'task_status': status,
            'task_progress': progress,
            'overall_progress': progress_info['progress_percentage'],
            'completed_tasks': progress_info['completed_tasks'],
            'failed_tasks': progress_info['failed_tasks'],
            'total_tasks': progress_info['total_tasks']
        })
    
    async def complete_tracking(self, execution_id: str, final_status: str):
        """進捗追跡を完了"""
        if execution_id not in self.execution_progress:
            return
        
        progress_info = self.execution_progress[execution_id]
        progress_info['completed_at'] = datetime.now().isoformat()
        progress_info['final_status'] = final_status
        
        await self.streaming_manager.stream_execution_progress(execution_id, {
            'type': 'tracking_completed',
            'final_status': final_status,
            'progress_percentage': 100.0,
            'completed_tasks': progress_info['completed_tasks'],
            'failed_tasks': progress_info['failed_tasks'],
            'total_tasks': progress_info['total_tasks']
        })
        
        # 追跡情報をクリーンアップ
        del self.execution_progress[execution_id]
    
    def get_execution_progress(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """実行の進捗情報を取得"""
        return self.execution_progress.get(execution_id)

class RealtimeCommunicationService:
    """リアルタイム通信サービス"""
    
    def __init__(self, socketio: SocketIO, redis_client: redis.Redis):
        self.websocket_manager = WebSocketManager(socketio, redis_client)
        self.streaming_manager = StreamingManager(self.websocket_manager)
        self.progress_tracker = ProgressTracker(self.streaming_manager)
    
    async def notify_user(self, user_id: str, notification_type: str, message: str, data: Dict[str, Any] = None):
        """ユーザーに通知を送信"""
        self.websocket_manager.send_to_user(user_id, 'notification', {
            'type': notification_type,
            'message': message,
            'data': data or {},
            'timestamp': datetime.now().isoformat()
        })
    
    async def broadcast_system_message(self, message: str, message_type: str = 'info'):
        """システムメッセージをブロードキャスト"""
        self.websocket_manager.broadcast('system_message', {
            'type': message_type,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    async def start_execution_session(self, execution_id: str, user_id: str, total_tasks: int):
        """実行セッションを開始"""
        # ストリーミングを開始
        stream_id = await self.streaming_manager.start_execution_stream(execution_id, user_id)
        
        # 進捗追跡を開始
        await self.progress_tracker.start_tracking(execution_id, total_tasks)
        
        return stream_id
    
    async def update_execution_progress(self, execution_id: str, task_id: str, status: str, progress: float = 0.0):
        """実行進捗を更新"""
        await self.progress_tracker.update_task_progress(execution_id, task_id, status, progress)
    
    async def log_execution_event(self, execution_id: str, event_type: str, message: str, data: Dict[str, Any] = None):
        """実行イベントをログ"""
        log_entry = {
            'event_type': event_type,
            'message': message,
            'data': data or {},
            'timestamp': datetime.now().isoformat()
        }
        
        await self.streaming_manager.stream_execution_log(execution_id, log_entry)
    
    async def stream_tool_result(self, execution_id: str, tool_name: str, result: Dict[str, Any]):
        """ツール実行結果をストリーミング"""
        await self.streaming_manager.stream_tool_output(execution_id, tool_name, result)
    
    async def end_execution_session(self, execution_id: str, final_result: Dict[str, Any]):
        """実行セッションを終了"""
        # 進捗追跡を完了
        final_status = final_result.get('status', 'completed')
        await self.progress_tracker.complete_tracking(execution_id, final_status)
        
        # ストリーミングを終了
        await self.streaming_manager.end_execution_stream(execution_id, final_result)
    
    async def stream_chat_response(self, user_id: str, response_generator):
        """チャット応答をストリーミング"""
        try:
            async for chunk in response_generator:
                await self.streaming_manager.stream_chat_response(user_id, chunk, False)
            
            # 最終チャンクを送信
            await self.streaming_manager.stream_chat_response(user_id, '', True)
            
        except Exception as e:
            logger.error(f"Error streaming chat response: {e}")
            await self.streaming_manager.stream_chat_response(user_id, f"エラー: {str(e)}", True)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """接続統計を取得"""
        return {
            'websocket_connections': self.websocket_manager.get_active_connections(),
            'active_streams': self.streaming_manager.get_active_streams(),
            'timestamp': datetime.now().isoformat()
        }

