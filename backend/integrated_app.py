"""
統合されたFlaskアプリケーション

このファイルは、全ての機能を統合したメインのFlaskアプリケーションです。
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import redis
import logging
import os
from datetime import datetime

# 各モジュールをインポート
from api_routes import api_bp
from workspace_api import workspace_bp, init_workspace_manager
from realtime_communication import RealtimeCommunicationService
from ai_agent_enhanced import EnhancedAIAgent
from tools.enhanced_tool_manager import EnhancedToolManager
from file_system_manager import FileSystemManager, ProjectManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Flaskアプリケーションを作成"""
    app = Flask(__name__)
    
    # 設定
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        'WORKSPACE_ROOT': os.environ.get('WORKSPACE_ROOT', '/tmp/autoai_workspace'),
        'REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,  # 100MB
        'UPLOAD_FOLDER': os.environ.get('UPLOAD_FOLDER', '/tmp/autoai_uploads'),
        'DATABASE_URL': os.environ.get('DATABASE_URL', 'sqlite:///autoai.db'),
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'GITHUB_TOKEN': os.environ.get('GITHUB_TOKEN'),
        'SMTP_SERVER': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'SMTP_PORT': int(os.environ.get('SMTP_PORT', '587')),
        'SMTP_USERNAME': os.environ.get('SMTP_USERNAME'),
        'SMTP_PASSWORD': os.environ.get('SMTP_PASSWORD'),
    })
    
    # CORS設定
    CORS(app, origins="*", supports_credentials=True)
    
    # SocketIO設定
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )
    
    # Redis接続
    try:
        redis_client = redis.from_url(app.config['REDIS_URL'])
        redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        redis_client = None
    
    # リアルタイム通信サービスを初期化
    realtime_service = RealtimeCommunicationService(socketio, redis_client)
    
    # ワークスペースマネージャーを初期化
    init_workspace_manager(app)
    
    # ツールマネージャーを初期化
    tool_manager = EnhancedToolManager()
    
    # AIエージェントを初期化
    ai_agent = EnhancedAIAgent(tool_manager, realtime_service)
    
    # アプリケーションコンテキストに追加
    app.realtime_service = realtime_service
    app.tool_manager = tool_manager
    app.ai_agent = ai_agent
    app.socketio = socketio
    
    # Blueprintを登録
    app.register_blueprint(api_bp)
    app.register_blueprint(workspace_bp)
    
    # ヘルスチェックエンドポイント
    @app.route('/health')
    def health_check():
        """ヘルスチェック"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'services': {
                'redis': redis_client is not None,
                'websocket': True,
                'ai_agent': True,
                'file_system': True
            }
        })
    
    # システム情報エンドポイント
    @app.route('/api/system/info')
    def system_info():
        """システム情報を取得"""
        return jsonify({
            'version': '1.0.0',
            'features': [
                'AI Agent',
                'Tool System',
                'File Management',
                'Project Management',
                'Real-time Communication',
                'WebSocket Support',
                'API Integration',
                'Web Scraping',
                'Email Support'
            ],
            'tools': tool_manager.list_tools() if tool_manager else [],
            'websocket_connections': realtime_service.get_connection_stats() if realtime_service else {}
        })
    
    # エラーハンドラー
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'message': 'The requested resource was not found on this server.'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'success': False,
            'error': 'File too large',
            'message': 'The uploaded file is too large. Maximum size is 100MB.'
        }), 413
    
    # リクエストログ
    @app.before_request
    def log_request_info():
        if request.endpoint != 'health_check':
            logger.info(f"{request.method} {request.url} - {request.remote_addr}")
    
    # レスポンスログ
    @app.after_request
    def log_response_info(response):
        if request.endpoint != 'health_check':
            logger.info(f"Response: {response.status_code}")
        return response
    
    return app, socketio

def main():
    """メイン関数"""
    app, socketio = create_app()
    
    # 開発環境での起動
    if os.environ.get('FLASK_ENV') == 'development':
        logger.info("Starting development server...")
        socketio.run(
            app,
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            debug=True,
            use_reloader=False  # SocketIOとの競合を避けるため
        )
    else:
        logger.info("Starting production server...")
        socketio.run(
            app,
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            debug=False
        )

if __name__ == '__main__':
    main()

