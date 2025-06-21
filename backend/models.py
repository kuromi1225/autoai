# データベースモデル定義

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import uuid

db = SQLAlchemy()

class User(db.Model):
    """ユーザーモデル"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    sessions = db.relationship('Session', backref='user', lazy=True, cascade='all, delete-orphan')

class Task(db.Model):
    """タスクモデル"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, planning, executing, completed, failed, cancelled
    priority = db.Column(db.String(10), default='medium')  # low, medium, high, urgent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # JSON フィールド
    task_metadata = db.Column(db.JSON, default=dict)  # 追加のメタデータ
    
    # リレーション
    plans = db.relationship('Plan', backref='task', lazy=True, cascade='all, delete-orphan')
    executions = db.relationship('Execution', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metadata': self.task_metadata
        }

class Plan(db.Model):
    """実行計画モデル"""
    __tablename__ = 'plans'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id'), nullable=False)
    version = db.Column(db.Integer, default=1)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')  # draft, approved, executing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # JSON フィールド
    steps = db.Column(db.JSON, default=list)  # 実行ステップのリスト
    estimated_duration = db.Column(db.Integer)  # 推定実行時間（分）
    required_tools = db.Column(db.JSON, default=list)  # 必要なツールのリスト
    
    # リレーション
    executions = db.relationship('Execution', backref='plan', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'version': self.version,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'steps': self.steps,
            'estimated_duration': self.estimated_duration,
            'required_tools': self.required_tools,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Execution(db.Model):
    """実行履歴モデル"""
    __tablename__ = 'executions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id'), nullable=False)
    plan_id = db.Column(db.String(36), db.ForeignKey('plans.id'), nullable=False)
    status = db.Column(db.String(20), default='running')  # running, completed, failed, cancelled
    current_step = db.Column(db.Integer, default=0)
    total_steps = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # JSON フィールド
    results = db.Column(db.JSON, default=dict)  # 実行結果
    error_info = db.Column(db.JSON, default=dict)  # エラー情報
    
    # リレーション
    logs = db.relationship('ExecutionLog', backref='execution', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'plan_id': self.plan_id,
            'status': self.status,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress': (self.current_step / self.total_steps * 100) if self.total_steps > 0 else 0,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'results': self.results,
            'error_info': self.error_info
        }

class ExecutionLog(db.Model):
    """実行ログモデル"""
    __tablename__ = 'execution_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = db.Column(db.String(36), db.ForeignKey('executions.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    log_level = db.Column(db.String(10), default='INFO')  # DEBUG, INFO, WARNING, ERROR
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # JSON フィールド
    log_metadata = db.Column(db.JSON, default=dict)  # 追加のメタデータ
    
    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'step_number': self.step_number,
            'log_level': self.log_level,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.log_metadata
        }

class Session(db.Model):
    """セッションモデル"""
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active, paused, completed, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # JSON フィールド
    context = db.Column(db.JSON, default=dict)  # セッションコンテキスト
    settings = db.Column(db.JSON, default=dict)  # セッション設定
    
    # リレーション
    messages = db.relationship('Message', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'context': self.context,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Message(db.Model):
    """メッセージモデル"""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user, assistant, system
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # JSON フィールド
    message_metadata = db.Column(db.JSON, default=dict)  # 追加のメタデータ
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.message_metadata
        }

class Tool(db.Model):
    """ツールモデル"""
    __tablename__ = 'tools'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)  # browser, file, code, api, etc.
    status = db.Column(db.String(20), default='active')  # active, inactive, maintenance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # JSON フィールド
    config = db.Column(db.JSON, default=dict)  # ツール設定
    schema = db.Column(db.JSON, default=dict)  # 入力スキーマ
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
            'status': self.status,
            'config': self.config,
            'schema': self.schema,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

