"""
JWT Authentication System

プロダクションレベルのJWT認証システムを実装
"""

import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, current_app
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """認証エラー"""
    pass

class AuthorizationError(Exception):
    """認可エラー"""
    pass

class JWTAuthManager:
    """JWT認証マネージャー"""
    
    def __init__(self, secret_key: str, algorithm: str = 'HS256'):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
        # ユーザーデータベース（本番環境では実際のDBを使用）
        self.users_db = {}
        self.refresh_tokens = {}
        
        # デフォルト管理者ユーザーを作成
        self._create_default_admin()
    
    def _create_default_admin(self):
        """デフォルト管理者ユーザーを作成"""
        admin_password = secrets.token_urlsafe(16)
        self.create_user(
            username='admin',
            email='admin@devin-ai-clone.local',
            password=admin_password,
            role='admin'
        )
        logger.info(f"Default admin user created with password: {admin_password}")
    
    def hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """パスワードを検証"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, username: str, email: str, password: str, role: str = 'user') -> Dict[str, Any]:
        """新しいユーザーを作成"""
        if username in self.users_db:
            raise ValueError(f"User {username} already exists")
        
        user_id = secrets.token_urlsafe(16)
        hashed_password = self.hash_password(password)
        
        user = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'role': role,
            'created_at': datetime.now(timezone.utc),
            'last_login': None,
            'is_active': True
        }
        
        self.users_db[username] = user
        logger.info(f"User created: {username} with role: {role}")
        
        return {
            'id': user_id,
            'username': username,
            'email': email,
            'role': role,
            'created_at': user['created_at'].isoformat()
        }
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """ユーザー認証"""
        user = self.users_db.get(username)
        if not user:
            return None
        
        if not user['is_active']:
            return None
        
        if not self.verify_password(password, user['password_hash']):
            return None
        
        # 最終ログイン時刻を更新
        user['last_login'] = datetime.now(timezone.utc)
        
        return {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role']
        }
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """アクセストークンを作成"""
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'role': user_data['role'],
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'access'
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """リフレッシュトークンを作成"""
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        token_id = secrets.token_urlsafe(32)
        
        payload = {
            'user_id': user_data['id'],
            'token_id': token_id,
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'refresh'
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # リフレッシュトークンを保存
        self.refresh_tokens[token_id] = {
            'user_id': user_data['id'],
            'created_at': datetime.now(timezone.utc),
            'expires_at': expire
        }
        
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """トークンを検証"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # トークンタイプの確認
            if payload.get('type') == 'refresh':
                # リフレッシュトークンの場合、データベースでも確認
                token_id = payload.get('token_id')
                if token_id not in self.refresh_tokens:
                    raise AuthenticationError("Invalid refresh token")
                
                stored_token = self.refresh_tokens[token_id]
                if stored_token['expires_at'] < datetime.now(timezone.utc):
                    del self.refresh_tokens[token_id]
                    raise AuthenticationError("Refresh token expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """アクセストークンをリフレッシュ"""
        payload = self.verify_token(refresh_token)
        
        if payload.get('type') != 'refresh':
            raise AuthenticationError("Invalid token type")
        
        user_id = payload['user_id']
        
        # ユーザー情報を取得
        user = None
        for username, user_data in self.users_db.items():
            if user_data['id'] == user_id:
                user = user_data
                break
        
        if not user or not user['is_active']:
            raise AuthenticationError("User not found or inactive")
        
        user_data = {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role']
        }
        
        # 新しいトークンペアを作成
        new_access_token = self.create_access_token(user_data)
        new_refresh_token = self.create_refresh_token(user_data)
        
        # 古いリフレッシュトークンを無効化
        old_token_id = payload.get('token_id')
        if old_token_id in self.refresh_tokens:
            del self.refresh_tokens[old_token_id]
        
        return new_access_token, new_refresh_token
    
    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """リフレッシュトークンを無効化"""
        try:
            payload = self.verify_token(refresh_token)
            token_id = payload.get('token_id')
            
            if token_id in self.refresh_tokens:
                del self.refresh_tokens[token_id]
                return True
            
        except AuthenticationError:
            pass
        
        return False
    
    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """トークンからユーザー情報を取得"""
        try:
            payload = self.verify_token(token)
            user_id = payload['user_id']
            
            # ユーザー情報を取得
            for username, user_data in self.users_db.items():
                if user_data['id'] == user_id:
                    return {
                        'id': user_data['id'],
                        'username': user_data['username'],
                        'email': user_data['email'],
                        'role': user_data['role']
                    }
            
        except AuthenticationError:
            pass
        
        return None


# グローバル認証マネージャー
auth_manager = None

def init_auth_manager(secret_key: str):
    """認証マネージャーを初期化"""
    global auth_manager
    auth_manager = JWTAuthManager(secret_key)
    return auth_manager

def get_auth_manager() -> JWTAuthManager:
    """認証マネージャーを取得"""
    global auth_manager
    if auth_manager is None:
        raise RuntimeError("Auth manager not initialized")
    return auth_manager

# デコレーター
def require_auth(f):
    """認証が必要なエンドポイント用デコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Authorization header missing'}), 401
        
        try:
            # Bearer トークンの形式を確認
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Invalid authorization header format'}), 401
            
            token = auth_header.split(' ')[1]
            auth_mgr = get_auth_manager()
            user = auth_mgr.get_user_from_token(token)
            
            if not user:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # リクエストにユーザー情報を追加
            request.current_user = user
            
        except AuthenticationError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(required_role: str):
    """特定のロールが必要なエンドポイント用デコレーター"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = getattr(request, 'current_user', None)
            
            if not user:
                return jsonify({'error': 'User not authenticated'}), 401
            
            user_role = user.get('role', 'user')
            
            # 管理者は全てのロールにアクセス可能
            if user_role == 'admin':
                return f(*args, **kwargs)
            
            # 要求されたロールと一致するかチェック
            if user_role != required_role:
                return jsonify({'error': f'Role {required_role} required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def create_auth_endpoints(app):
    """認証関連のエンドポイントを作成"""
    
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        """ユーザー登録"""
        data = request.get_json()
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({'error': 'Username, email, and password are required'}), 400
        
        try:
            auth_mgr = get_auth_manager()
            user = auth_mgr.create_user(username, email, password)
            
            return jsonify({
                'success': True,
                'message': 'User created successfully',
                'user': user
            }), 201
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return jsonify({'error': 'Registration failed'}), 500
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """ユーザーログイン"""
        data = request.get_json()
        
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return jsonify({'error': 'Username and password are required'}), 400
        
        try:
            auth_mgr = get_auth_manager()
            user = auth_mgr.authenticate_user(username, password)
            
            if not user:
                return jsonify({'error': 'Invalid credentials'}), 401
            
            access_token = auth_mgr.create_access_token(user)
            refresh_token = auth_mgr.create_refresh_token(user)
            
            return jsonify({
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user
            })
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'error': 'Login failed'}), 500
    
    @app.route('/api/auth/refresh', methods=['POST'])
    def refresh():
        """トークンリフレッシュ"""
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token is required'}), 400
        
        try:
            auth_mgr = get_auth_manager()
            new_access_token, new_refresh_token = auth_mgr.refresh_access_token(refresh_token)
            
            return jsonify({
                'success': True,
                'access_token': new_access_token,
                'refresh_token': new_refresh_token
            })
            
        except AuthenticationError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return jsonify({'error': 'Token refresh failed'}), 500
    
    @app.route('/api/auth/logout', methods=['POST'])
    @require_auth
    def logout():
        """ユーザーログアウト"""
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if refresh_token:
            auth_mgr = get_auth_manager()
            auth_mgr.revoke_refresh_token(refresh_token)
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
    
    @app.route('/api/auth/me', methods=['GET'])
    @require_auth
    def get_current_user():
        """現在のユーザー情報を取得"""
        user = getattr(request, 'current_user', None)
        return jsonify({
            'success': True,
            'user': user
        })
    
    @app.route('/api/auth/users', methods=['GET'])
    @require_role('admin')
    def list_users():
        """ユーザー一覧を取得（管理者のみ）"""
        auth_mgr = get_auth_manager()
        
        users = []
        for username, user_data in auth_mgr.users_db.items():
            users.append({
                'id': user_data['id'],
                'username': user_data['username'],
                'email': user_data['email'],
                'role': user_data['role'],
                'created_at': user_data['created_at'].isoformat(),
                'last_login': user_data['last_login'].isoformat() if user_data['last_login'] else None,
                'is_active': user_data['is_active']
            })
        
        return jsonify({
            'success': True,
            'users': users
        })

