"""
Devin AI Clone - 認証システム

基本的な認証機能を提供します。
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app

class AuthService:
    """認証サービスクラス"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Flaskアプリケーションを初期化"""
        self.app = app
        
        # デフォルトユーザーの設定（開発用）
        self.default_users = {
            'admin': {
                'username': 'admin',
                'password_hash': bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'role': 'admin',
                'email': 'admin@devin-ai.local'
            },
            'user': {
                'username': 'user',
                'password_hash': bcrypt.hashpw('user123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'role': 'user',
                'email': 'user@devin-ai.local'
            },
            'demo': {
                'username': 'demo',
                'password_hash': bcrypt.hashpw('demo123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'role': 'demo',
                'email': 'demo@devin-ai.local'
            }
        }
    
    def get_secret_key(self):
        """JWT秘密鍵を取得"""
        secret_path = '/run/secrets/jwt_secret_key'
        if os.path.exists(secret_path):
            with open(secret_path, 'r') as f:
                return f.read().strip()
        return self.app.config.get('SECRET_KEY', 'dev-secret-key')
    
    def verify_password(self, username, password):
        """パスワードを検証"""
        user = self.default_users.get(username)
        if not user:
            return False
        
        return bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8'))
    
    def get_user(self, username):
        """ユーザー情報を取得"""
        user = self.default_users.get(username)
        if user:
            # パスワードハッシュを除外して返す
            return {
                'username': user['username'],
                'role': user['role'],
                'email': user['email']
            }
        return None
    
    def generate_token(self, username):
        """JWTトークンを生成"""
        user = self.get_user(username)
        if not user:
            return None
        
        payload = {
            'username': username,
            'role': user['role'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.get_secret_key(), algorithm='HS256')
    
    def verify_token(self, token):
        """JWTトークンを検証"""
        try:
            payload = jwt.decode(token, self.get_secret_key(), algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def login(self, username, password):
        """ログイン処理"""
        if self.verify_password(username, password):
            token = self.generate_token(username)
            user = self.get_user(username)
            return {
                'success': True,
                'token': token,
                'user': user,
                'expires_in': 24 * 3600  # 24時間（秒）
            }
        return {
            'success': False,
            'message': 'ユーザー名またはパスワードが正しくありません'
        }
    
    def refresh_token(self, token):
        """トークンをリフレッシュ"""
        payload = self.verify_token(token)
        if payload:
            # 新しいトークンを生成
            new_token = self.generate_token(payload['username'])
            return {
                'success': True,
                'token': new_token,
                'expires_in': 24 * 3600
            }
        return {
            'success': False,
            'message': 'トークンが無効です'
        }

def require_auth(f):
    """認証が必要なエンドポイントのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Authorizationヘッダーからトークンを取得
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # "Bearer <token>"
            except IndexError:
                return jsonify({'error': 'トークンの形式が正しくありません'}), 401
        
        if not token:
            return jsonify({'error': '認証トークンが必要です'}), 401
        
        # トークンを検証
        auth_service = current_app.auth_service
        payload = auth_service.verify_token(token)
        
        if not payload:
            return jsonify({'error': 'トークンが無効または期限切れです'}), 401
        
        # リクエストにユーザー情報を追加
        request.current_user = payload
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(required_role):
    """特定の役割が必要なエンドポイントのデコレータ"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_role = request.current_user.get('role')
            
            if user_role != required_role and user_role != 'admin':
                return jsonify({'error': '権限が不足しています'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

