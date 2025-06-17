"""
Enhanced Flask Application with JWT Authentication

JWT認証システムを統合したFlaskアプリケーション
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from services.jwt_auth import init_auth_manager, create_auth_endpoints, require_auth, require_role
from api_blueprints import register_blueprints
import secrets

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Flaskアプリケーションファクトリー"""
    app = Flask(__name__)
    
    # 設定
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
    app.config['CORS_ORIGINS'] = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # CORS設定
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-User-ID'])
    
    # SocketIO設定
    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config['CORS_ORIGINS'],
        async_mode='threading'
    )
    
    # JWT認証マネージャーの初期化
    auth_manager = init_auth_manager(app.config['JWT_SECRET_KEY'])
    
    # 認証エンドポイントの作成
    create_auth_endpoints(app)
    
    # APIブループリントの登録
    register_blueprints(app)
    
    # ヘルスチェックエンドポイント
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """ヘルスチェック"""
        return jsonify({
            'status': 'healthy',
            'service': 'devin-ai-clone-backend',
            'version': '2.0.0'
        })
    
    # 保護されたテストエンドポイント
    @app.route('/api/protected', methods=['GET'])
    @require_auth
    def protected_endpoint():
        """認証が必要なテストエンドポイント"""
        user = getattr(request, 'current_user', None)
        return jsonify({
            'message': 'This is a protected endpoint',
            'user': user
        })
    
    # 管理者専用エンドポイント
    @app.route('/api/admin/stats', methods=['GET'])
    @require_role('admin')
    def admin_stats():
        """管理者専用統計エンドポイント"""
        return jsonify({
            'message': 'Admin statistics',
            'total_users': len(auth_manager.users_db),
            'active_tokens': len(auth_manager.refresh_tokens)
        })
    
    # チャットエンドポイント（認証必須）
    @app.route('/api/chat', methods=['POST'])
    @require_auth
    def chat():
        """チャットエンドポイント（認証必須）"""
        data = request.get_json()
        user = getattr(request, 'current_user', None)
        
        message = data.get('message', '')
        
        # 簡単なレスポンス生成
        response = f"Hello {user['username']}, you said: {message}"
        
        # 実際のAI処理はここに実装
        # TODO: Qwen AIモデルとの連携
        
        return jsonify({
            'response': response,
            'user_id': user['id'],
            'plan': None  # 計画生成は別途実装
        })
    
    # 計画実行エンドポイント（認証必須）
    @app.route('/api/execute_plan', methods=['POST'])
    @require_auth
    def execute_plan():
        """計画実行エンドポイント（認証必須）"""
        data = request.get_json()
        user = getattr(request, 'current_user', None)
        
        plan_id = data.get('plan_id')
        
        if not plan_id:
            return jsonify({
                'success': False,
                'error': 'Plan ID is required'
            }), 400
        
        # 計画実行の実装
        # TODO: 実際の計画実行ロジック
        
        return jsonify({
            'success': True,
            'message': f'Plan {plan_id} execution started for user {user["username"]}',
            'plan_id': plan_id
        })
    
    # WebSocketイベント
    @socketio.on('connect')
    def handle_connect(auth):
        """WebSocket接続時の認証"""
        try:
            # トークンベース認証
            token = auth.get('token') if auth else None
            if token:
                user = auth_manager.get_user_from_token(token)
                if user:
                    logger.info(f"User {user['username']} connected via WebSocket")
                    return True
            
            logger.warning("Unauthorized WebSocket connection attempt")
            return False
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            return False
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """WebSocket切断"""
        logger.info("User disconnected from WebSocket")
    
    # エラーハンドラー
    @app.errorhandler(401)
    def unauthorized(error):
        """401エラーハンドラー"""
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """403エラーハンドラー"""
        return jsonify({
            'error': 'Forbidden',
            'message': 'Insufficient permissions'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """404エラーハンドラー"""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500エラーハンドラー"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    return app, socketio

# アプリケーションの作成
app, socketio = create_app()

if __name__ == '__main__':
    # 開発環境での実行
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Devin AI Clone Backend on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True
    )

