"""
Simplified Devin AI Clone Backend for Testing

This is a simplified version of the backend for testing purposes.
It includes basic Flask functionality without heavy dependencies.
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import time

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask アプリケーションの初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'devin-ai-clone-secret-key'

# CORS設定
CORS(app, origins="*")

# SocketIO設定
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading'
)

# シンプルなメモリストレージ
tasks = {}
plans = {}

@app.route("/")
def index():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'running',
        'message': 'Devin AI Clone Backend (Test Mode)',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route("/api/health")
def health():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    """チャットエンドポイント"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        logger.info(f"Received chat message: {message}")
        
        # シンプルなレスポンス生成
        response = f"受信しました: {message}\n\nタスクを分析し、実行計画を作成しています..."
        
        # シンプルな計画を生成
        plan = {
            'plan_id': f'plan_{int(time.time())}',
            'title': 'Webアプリケーションの作成',
            'description': f'「{message}」に基づいたWebアプリケーションを作成します',
            'steps': [
                {
                    'id': 'step_1',
                    'title': '要件分析',
                    'description': 'タスクの詳細を分析し、技術要件を決定',
                    'estimated_time': 300,
                    'risk_level': 'low',
                    'reversible': True
                },
                {
                    'id': 'step_2',
                    'title': 'プロジェクト構造作成',
                    'description': 'Webアプリケーションのディレクトリ構造を作成',
                    'estimated_time': 180,
                    'risk_level': 'low',
                    'reversible': True
                },
                {
                    'id': 'step_3',
                    'title': 'コード実装',
                    'description': 'フロントエンドとバックエンドを実装',
                    'estimated_time': 1800,
                    'risk_level': 'medium',
                    'reversible': True
                },
                {
                    'id': 'step_4',
                    'title': 'テスト実行',
                    'description': '機能テストと統合テストを実行',
                    'estimated_time': 600,
                    'risk_level': 'low',
                    'reversible': True
                },
                {
                    'id': 'step_5',
                    'title': 'GitHubコミット',
                    'description': '完成したコードをGitHubにコミット',
                    'estimated_time': 300,
                    'risk_level': 'low',
                    'reversible': False
                }
            ],
            'estimated_total_time': 3180,
            'risk_assessment': {
                'overall_risk': 'medium',
                'high_risk_steps': 0,
                'medium_risk_steps': 1,
                'irreversible_steps': 1
            }
        }
        
        plans[plan['plan_id']] = plan
        
        return jsonify({
            'response': response,
            'plan': plan,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route("/api/execute_plan", methods=["POST"])
def execute_plan():
    """計画実行エンドポイント"""
    try:
        data = request.get_json()
        plan_id = data.get('plan_id', '')
        
        logger.info(f"Executing plan: {plan_id}")
        
        if plan_id not in plans:
            return jsonify({
                'error': 'Plan not found',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
        
        # 非同期で計画実行をシミュレート
        socketio.start_background_task(execute_plan_simulation, plan_id)
        
        return jsonify({
            'message': 'Plan execution started',
            'plan_id': plan_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Plan execution error: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

def execute_plan_simulation(plan_id):
    """計画実行のシミュレーション"""
    try:
        plan = plans.get(plan_id)
        if not plan:
            return
        
        logger.info(f"Starting plan simulation: {plan_id}")
        
        # 計画実行開始の通知
        socketio.emit('plan_execution_started', {
            'plan_id': plan_id,
            'message': '計画の実行を開始しました'
        })
        
        steps = plan['steps']
        
        # 各ステップを順次実行
        for i, step in enumerate(steps):
            try:
                # ステップ開始の通知
                socketio.emit('step_started', {
                    'plan_id': plan_id,
                    'step_id': step['id'],
                    'step_index': i,
                    'step_title': step['title']
                })
                
                # ステップの実行（シミュレーション）
                execution_time = min(step['estimated_time'] / 100, 10)  # 最大10秒
                
                # 進捗の更新
                for progress in range(0, 101, 25):
                    socketio.sleep(execution_time / 4)
                    socketio.emit('step_progress', {
                        'plan_id': plan_id,
                        'step_id': step['id'],
                        'progress': progress,
                        'message': f'{step["title"]} - {progress}%完了'
                    })
                
                # ステップ完了の通知
                socketio.emit('step_completed', {
                    'plan_id': plan_id,
                    'step_id': step['id'],
                    'step_index': i,
                    'result': f'{step["title"]}が正常に完了しました'
                })
                
                # 全体の進捗を更新
                overall_progress = int((i + 1) / len(steps) * 100)
                socketio.emit('plan_progress', {
                    'plan_id': plan_id,
                    'progress': overall_progress,
                    'completed_steps': i + 1,
                    'total_steps': len(steps)
                })
                
            except Exception as step_error:
                logger.error(f"Step execution failed: {step['id']}, error: {step_error}")
                
                # ステップ失敗の通知
                socketio.emit('step_failed', {
                    'plan_id': plan_id,
                    'step_id': step['id'],
                    'step_index': i,
                    'error': str(step_error)
                })
                
                # 計画全体を失敗として処理
                socketio.emit('plan_execution_failed', {
                    'plan_id': plan_id,
                    'failed_step': step['id'],
                    'error': str(step_error)
                })
                return
        
        # 計画完了の通知
        socketio.emit('plan_execution_completed', {
            'plan_id': plan_id,
            'status': 'completed',
            'message': '計画が正常に完了しました',
            'completed_steps': len(steps)
        })
        
        logger.info(f"Plan execution completed: {plan_id}")
        
    except Exception as e:
        logger.error(f"Plan execution failed: {plan_id}, error: {e}")
        
        socketio.emit('plan_execution_failed', {
            'plan_id': plan_id,
            'error': str(e)
        })

# WebSocketイベント
@socketio.on('connect')
def handle_connect():
    """WebSocket接続イベント"""
    logger.info(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to Devin AI Clone (Test Mode)'})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket切断イベント"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('message')
def handle_message(data):
    """WebSocketメッセージイベント"""
    logger.info(f"Received message: {data}")
    
    # エコー応答
    emit('response', {
        'message': f"Echo: {data.get('message', '')}",
        'timestamp': datetime.utcnow().isoformat()
    })

# エラーハンドラー
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # 開発環境での実行
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5001,  # ポートを5001に変更
        debug=True,
        allow_unsafe_werkzeug=True
    )

