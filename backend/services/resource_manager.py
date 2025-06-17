"""
Resource Management Service

ACU (Agent Compute Unit) の概念を実装したリソース管理サービス
"""

import os
import time
import psutil
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class ResourceLimits:
    """リソース制限の設定"""
    max_cpu_percent: float = 80.0
    max_memory_mb: int = 2048
    max_execution_time: int = 300
    max_processes: int = 50
    max_file_size_mb: int = 100
    max_network_requests: int = 100

@dataclass
class ResourceUsage:
    """リソース使用量の記録"""
    cpu_percent: float
    memory_mb: float
    execution_time: float
    process_count: int
    network_requests: int
    timestamp: datetime

class ACUManager:
    """Agent Compute Unit マネージャー"""
    
    def __init__(self):
        self.default_limits = ResourceLimits()
        self.user_limits = {}  # ユーザーごとのリソース制限
        self.usage_history = {}  # ユーザーごとの使用履歴
        self.active_tasks = {}  # 実行中のタスク
        self.lock = threading.Lock()
        
        # 設定の読み込み
        self._load_config()
        
        # 監視スレッドの開始
        self.monitoring_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitoring_thread.start()
    
    def _load_config(self):
        """環境変数から設定を読み込み"""
        self.default_limits.max_cpu_percent = float(os.getenv('MAX_CPU_PERCENT', '80'))
        self.default_limits.max_memory_mb = int(os.getenv('MAX_MEMORY_MB', '2048'))
        self.default_limits.max_execution_time = int(os.getenv('MAX_EXECUTION_TIME', '300'))
        self.default_limits.max_processes = int(os.getenv('MAX_PROCESSES', '50'))
        self.default_limits.max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
        self.default_limits.max_network_requests = int(os.getenv('MAX_NETWORK_REQUESTS', '100'))
    
    def set_user_limits(self, user_id: str, limits: ResourceLimits) -> bool:
        """ユーザー固有のリソース制限を設定"""
        try:
            with self.lock:
                self.user_limits[user_id] = limits
            logger.info(f"Resource limits set for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to set user limits: {e}")
            return False
    
    def get_user_limits(self, user_id: str) -> ResourceLimits:
        """ユーザーのリソース制限を取得"""
        return self.user_limits.get(user_id, self.default_limits)
    
    def check_resource_availability(self, user_id: str, estimated_usage: Dict[str, Any]) -> Dict[str, Any]:
        """リソースの利用可能性をチェック"""
        limits = self.get_user_limits(user_id)
        current_usage = self._get_current_usage(user_id)
        
        # 各リソースの利用可能性をチェック
        checks = {
            'cpu_available': current_usage.cpu_percent + estimated_usage.get('cpu_percent', 0) <= limits.max_cpu_percent,
            'memory_available': current_usage.memory_mb + estimated_usage.get('memory_mb', 0) <= limits.max_memory_mb,
            'execution_time_ok': estimated_usage.get('execution_time', 0) <= limits.max_execution_time,
            'process_count_ok': current_usage.process_count + estimated_usage.get('process_count', 1) <= limits.max_processes
        }
        
        all_available = all(checks.values())
        
        return {
            'available': all_available,
            'checks': checks,
            'current_usage': current_usage.__dict__,
            'limits': limits.__dict__,
            'estimated_usage': estimated_usage
        }
    
    def allocate_resources(self, user_id: str, task_id: str, estimated_usage: Dict[str, Any]) -> bool:
        """リソースを割り当て"""
        availability = self.check_resource_availability(user_id, estimated_usage)
        
        if not availability['available']:
            logger.warning(f"Resource allocation failed for user {user_id}, task {task_id}")
            return False
        
        with self.lock:
            if user_id not in self.active_tasks:
                self.active_tasks[user_id] = {}
            
            self.active_tasks[user_id][task_id] = {
                'start_time': datetime.now(),
                'estimated_usage': estimated_usage,
                'actual_usage': ResourceUsage(0, 0, 0, 0, 0, datetime.now())
            }
        
        logger.info(f"Resources allocated for user {user_id}, task {task_id}")
        return True
    
    def release_resources(self, user_id: str, task_id: str) -> bool:
        """リソースを解放"""
        try:
            with self.lock:
                if user_id in self.active_tasks and task_id in self.active_tasks[user_id]:
                    task_info = self.active_tasks[user_id][task_id]
                    
                    # 使用履歴に記録
                    if user_id not in self.usage_history:
                        self.usage_history[user_id] = []
                    
                    self.usage_history[user_id].append({
                        'task_id': task_id,
                        'start_time': task_info['start_time'],
                        'end_time': datetime.now(),
                        'estimated_usage': task_info['estimated_usage'],
                        'actual_usage': task_info['actual_usage'].__dict__
                    })
                    
                    # 古い履歴を削除（30日以上前）
                    cutoff_date = datetime.now() - timedelta(days=30)
                    self.usage_history[user_id] = [
                        h for h in self.usage_history[user_id] 
                        if h['end_time'] > cutoff_date
                    ]
                    
                    del self.active_tasks[user_id][task_id]
                    
                    if not self.active_tasks[user_id]:
                        del self.active_tasks[user_id]
            
            logger.info(f"Resources released for user {user_id}, task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to release resources: {e}")
            return False
    
    def update_task_usage(self, user_id: str, task_id: str, usage: ResourceUsage) -> bool:
        """タスクのリソース使用量を更新"""
        try:
            with self.lock:
                if (user_id in self.active_tasks and 
                    task_id in self.active_tasks[user_id]):
                    self.active_tasks[user_id][task_id]['actual_usage'] = usage
            return True
        except Exception as e:
            logger.error(f"Failed to update task usage: {e}")
            return False
    
    def _get_current_usage(self, user_id: str) -> ResourceUsage:
        """現在のリソース使用量を取得"""
        try:
            # システム全体の使用量を取得
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
            
            # ユーザーのアクティブタスク数
            process_count = len(self.active_tasks.get(user_id, {}))
            
            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                execution_time=0,  # 個別タスクで管理
                process_count=process_count,
                network_requests=0,  # 個別タスクで管理
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Failed to get current usage: {e}")
            return ResourceUsage(0, 0, 0, 0, 0, datetime.now())
    
    def _monitor_resources(self):
        """リソース監視スレッド"""
        while True:
            try:
                with self.lock:
                    for user_id, tasks in self.active_tasks.items():
                        limits = self.get_user_limits(user_id)
                        
                        for task_id, task_info in tasks.items():
                            # 実行時間のチェック
                            elapsed_time = (datetime.now() - task_info['start_time']).total_seconds()
                            
                            if elapsed_time > limits.max_execution_time:
                                logger.warning(f"Task {task_id} for user {user_id} exceeded time limit")
                                # タスクの強制終了処理をここに実装
                                # self._terminate_task(user_id, task_id)
                
                time.sleep(10)  # 10秒間隔で監視
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                time.sleep(30)  # エラー時は30秒待機
    
    def get_usage_statistics(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """使用統計を取得"""
        try:
            if user_id not in self.usage_history:
                return {
                    'total_tasks': 0,
                    'total_execution_time': 0,
                    'average_cpu_usage': 0,
                    'average_memory_usage': 0,
                    'peak_usage': None
                }
            
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [
                h for h in self.usage_history[user_id]
                if h['end_time'] > cutoff_date
            ]
            
            if not recent_history:
                return {
                    'total_tasks': 0,
                    'total_execution_time': 0,
                    'average_cpu_usage': 0,
                    'average_memory_usage': 0,
                    'peak_usage': None
                }
            
            total_tasks = len(recent_history)
            total_execution_time = sum(
                (h['end_time'] - h['start_time']).total_seconds()
                for h in recent_history
            )
            
            cpu_usages = [h['actual_usage']['cpu_percent'] for h in recent_history]
            memory_usages = [h['actual_usage']['memory_mb'] for h in recent_history]
            
            return {
                'total_tasks': total_tasks,
                'total_execution_time': total_execution_time,
                'average_cpu_usage': sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0,
                'average_memory_usage': sum(memory_usages) / len(memory_usages) if memory_usages else 0,
                'peak_cpu_usage': max(cpu_usages) if cpu_usages else 0,
                'peak_memory_usage': max(memory_usages) if memory_usages else 0,
                'recent_tasks': recent_history[-10:]  # 最新10件
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage statistics: {e}")
            return {
                'total_tasks': 0,
                'total_execution_time': 0,
                'average_cpu_usage': 0,
                'average_memory_usage': 0,
                'peak_usage': None
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム全体のステータスを取得"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            active_users = len(self.active_tasks)
            total_active_tasks = sum(len(tasks) for tasks in self.active_tasks.values())
            
            return {
                'system_cpu_percent': cpu_percent,
                'system_memory_percent': memory.percent,
                'system_memory_used_mb': memory.used / 1024 / 1024,
                'system_memory_total_mb': memory.total / 1024 / 1024,
                'system_disk_percent': disk.percent,
                'active_users': active_users,
                'total_active_tasks': total_active_tasks,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'system_cpu_percent': 0,
                'system_memory_percent': 0,
                'system_memory_used_mb': 0,
                'system_memory_total_mb': 0,
                'system_disk_percent': 0,
                'active_users': 0,
                'total_active_tasks': 0,
                'timestamp': datetime.now().isoformat()
            }

# グローバルインスタンス
acu_manager = ACUManager()

def create_resource_management_api(app, db):
    """リソース管理APIエンドポイントを作成"""
    
    @app.route('/api/resources/limits', methods=['GET'])
    def get_resource_limits():
        """リソース制限を取得"""
        user_id = request.headers.get('X-User-ID', 'default')
        limits = acu_manager.get_user_limits(user_id)
        
        return jsonify(limits.__dict__)
    
    @app.route('/api/resources/limits', methods=['POST'])
    def set_resource_limits():
        """リソース制限を設定"""
        user_id = request.headers.get('X-User-ID', 'default')
        data = request.get_json()
        
        try:
            limits = ResourceLimits(
                max_cpu_percent=data.get('max_cpu_percent', 80.0),
                max_memory_mb=data.get('max_memory_mb', 2048),
                max_execution_time=data.get('max_execution_time', 300),
                max_processes=data.get('max_processes', 50),
                max_file_size_mb=data.get('max_file_size_mb', 100),
                max_network_requests=data.get('max_network_requests', 100)
            )
            
            success = acu_manager.set_user_limits(user_id, limits)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'リソース制限を設定しました'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'リソース制限の設定に失敗しました'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'設定エラー: {str(e)}'
            }), 400
    
    @app.route('/api/resources/usage', methods=['GET'])
    def get_resource_usage():
        """リソース使用量を取得"""
        user_id = request.headers.get('X-User-ID', 'default')
        days = int(request.args.get('days', 7))
        
        statistics = acu_manager.get_usage_statistics(user_id, days)
        return jsonify(statistics)
    
    @app.route('/api/resources/status', methods=['GET'])
    def get_system_status():
        """システムステータスを取得"""
        status = acu_manager.get_system_status()
        return jsonify(status)
    
    @app.route('/api/resources/check', methods=['POST'])
    def check_resource_availability():
        """リソース利用可能性をチェック"""
        user_id = request.headers.get('X-User-ID', 'default')
        data = request.get_json()
        
        estimated_usage = data.get('estimated_usage', {})
        availability = acu_manager.check_resource_availability(user_id, estimated_usage)
        
        return jsonify(availability)

