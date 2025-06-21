"""
AutoAI v3.0 統合Flaskアプリケーション

QwQ-32B、MCP、VSCode、Git、マルチエージェントシステムを統合
"""

import os
import asyncio
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
from datetime import datetime
import json

# AutoAI モジュール
from qwq_inference_engine import QwQInferenceEngine, get_qwq_engine
from mcp_server import get_mcp_server, start_mcp_server
from vscode_integration import get_vscode_integration, initialize_vscode_integration
from git_manager import get_git_manager, initialize_git_manager
from multi_agent_system import get_multi_agent_system, initialize_multi_agent_system, AgentRole, TaskPriority

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask アプリケーション
app = Flask(__name__)
app.config['SECRET_KEY'] = 'autoai_v3_secret_key'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# グローバル変数
qwq_engine = None
mcp_server = None
vscode_integration = None
git_manager = None
multi_agent_system = None
system_stats = {
    "start_time": time.time(),
    "total_requests": 0,
    "active_connections": 0
}

@app.before_first_request
async def initialize_systems():
    """システム初期化"""
    global qwq_engine, mcp_server, vscode_integration, git_manager, multi_agent_system
    
    try:
        logger.info("Initializing AutoAI v3.0 systems...")
        
        # QwQ-32B エンジン初期化
        logger.info("Initializing QwQ-32B inference engine...")
        qwq_engine = QwQInferenceEngine()
        await qwq_engine.initialize()
        
        # MCP サーバー初期化
        logger.info("Starting MCP server...")
        mcp_server = await start_mcp_server("localhost", 8765)
        
        # VSCode 統合初期化
        logger.info("Initializing VSCode integration...")
        success = await initialize_vscode_integration("/tmp/autoai_workspace")
        if not success:
            logger.warning("VSCode integration initialization failed")
        
        # Git 管理初期化
        logger.info("Initializing Git manager...")
        git_manager = initialize_git_manager("/tmp/autoai_workspace")
        
        # マルチエージェントシステム初期化
        logger.info("Initializing multi-agent system...")
        multi_agent_system = await initialize_multi_agent_system(qwq_engine)
        
        logger.info("All systems initialized successfully!")
        
    except Exception as e:
        logger.error(f"System initialization failed: {e}")

# ===== API エンドポイント =====

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time() - system_stats["start_time"],
        "systems": {
            "qwq_engine": qwq_engine is not None and qwq_engine.is_loaded,
            "mcp_server": mcp_server is not None and mcp_server.is_running,
            "vscode": vscode_integration is not None and vscode_integration.is_running,
            "git_manager": git_manager is not None,
            "multi_agent": multi_agent_system is not None and multi_agent_system.is_running
        }
    })

@app.route('/api/qwq/generate', methods=['POST'])
async def qwq_generate():
    """QwQ-32B推論API"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        max_length = data.get('max_length', 512)
        temperature = data.get('temperature', 0.7)
        
        if not qwq_engine or not qwq_engine.is_loaded:
            return jsonify({"error": "QwQ engine not available"}), 503
        
        response = await qwq_engine.generate_response_async(
            prompt, max_length=max_length, temperature=temperature
        )
        
        system_stats["total_requests"] += 1
        
        return jsonify({
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"QwQ generation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/status', methods=['GET'])
def mcp_status():
    """MCP サーバー状態"""
    if not mcp_server:
        return jsonify({"error": "MCP server not available"}), 503
    
    stats = mcp_server.stats.get_stats()
    return jsonify({
        "status": "running" if mcp_server.is_running else "stopped",
        "stats": stats,
        "tools_count": len(mcp_server.tools),
        "active_connections": len(mcp_server.clients)
    })

@app.route('/api/vscode/status', methods=['GET'])
def vscode_status():
    """VSCode 統合状態"""
    if not vscode_integration:
        return jsonify({"error": "VSCode integration not available"}), 503
    
    status = vscode_integration.get_status()
    return jsonify(status)

@app.route('/api/vscode/ask_assistant', methods=['POST'])
async def vscode_ask_assistant():
    """VSCode AI アシスタント"""
    try:
        data = request.get_json()
        code = data.get('code', '')
        question = data.get('question', '')
        language = data.get('language', 'python')
        
        prompt = f"""
        Code Analysis Request:
        Language: {language}
        Code: {code}
        Question: {question}
        
        Please provide a helpful and detailed response about the code.
        """
        
        response = await qwq_engine.generate_response_async(prompt)
        
        return jsonify({"response": response})
        
    except Exception as e:
        logger.error(f"VSCode assistant error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/vscode/generate_code', methods=['POST'])
async def vscode_generate_code():
    """VSCode コード生成"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        language = data.get('language', 'python')
        context = data.get('context', '')
        
        full_prompt = f"""
        Generate {language} code for the following request:
        
        Request: {prompt}
        Context: {context}
        
        Please provide clean, well-commented code that follows best practices.
        """
        
        response = await qwq_engine.generate_response_async(full_prompt)
        
        return jsonify({"response": response})
        
    except Exception as e:
        logger.error(f"Code generation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/git/status', methods=['GET'])
def git_status():
    """Git 状態"""
    if not git_manager:
        return jsonify({"error": "Git manager not available"}), 503
    
    status = git_manager.get_status()
    if status:
        return jsonify({
            "status": status.__dict__,
            "info": git_manager.get_git_info()
        })
    else:
        return jsonify({"error": "No active repository"}), 404

@app.route('/api/git/clone', methods=['POST'])
async def git_clone():
    """Git クローン"""
    try:
        data = request.get_json()
        url = data.get('url', '')
        local_path = data.get('local_path')
        branch = data.get('branch')
        
        success = await git_manager.clone_repository(url, local_path, branch)
        
        if success:
            return jsonify({"message": "Repository cloned successfully"})
        else:
            return jsonify({"error": "Clone failed"}), 500
            
    except Exception as e:
        logger.error(f"Git clone error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/git/commit', methods=['POST'])
async def git_commit():
    """Git コミット"""
    try:
        data = request.get_json()
        message = data.get('message')
        files = data.get('files')
        auto_stage = data.get('auto_stage', True)
        
        success = await git_manager.commit_changes(message, files, auto_stage)
        
        if success:
            return jsonify({"message": "Changes committed successfully"})
        else:
            return jsonify({"error": "Commit failed"}), 500
            
    except Exception as e:
        logger.error(f"Git commit error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/status', methods=['GET'])
def agents_status():
    """エージェント状態"""
    if not multi_agent_system:
        return jsonify({"error": "Multi-agent system not available"}), 503
    
    status = multi_agent_system.get_system_status()
    return jsonify(status)

@app.route('/api/agents/submit_task', methods=['POST'])
async def submit_task():
    """タスク投入"""
    try:
        data = request.get_json()
        title = data.get('title', '')
        description = data.get('description', '')
        role = AgentRole(data.get('role', 'pg'))
        priority = TaskPriority(data.get('priority', 'medium'))
        
        task_id = await multi_agent_system.submit_task(title, description, role, priority)
        
        return jsonify({
            "task_id": task_id,
            "message": "Task submitted successfully"
        })
        
    except Exception as e:
        logger.error(f"Task submission error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """タスク状態取得"""
    if not multi_agent_system:
        return jsonify({"error": "Multi-agent system not available"}), 503
    
    task_status = multi_agent_system.get_task_status(task_id)
    if task_status:
        return jsonify(task_status)
    else:
        return jsonify({"error": "Task not found"}), 404

@app.route('/api/system/stats', methods=['GET'])
def system_statistics():
    """システム統計"""
    stats = {
        "uptime": time.time() - system_stats["start_time"],
        "total_requests": system_stats["total_requests"],
        "active_connections": system_stats["active_connections"],
        "timestamp": datetime.now().isoformat()
    }
    
    # 各システムの統計を追加
    if mcp_server:
        stats["mcp"] = mcp_server.stats.get_stats()
    
    if vscode_integration:
        stats["vscode"] = vscode_integration.get_status()
    
    if git_manager:
        stats["git"] = git_manager.get_git_info()
    
    if multi_agent_system:
        stats["agents"] = multi_agent_system.get_system_status()
    
    return jsonify(stats)

# ===== WebSocket イベント =====

@socketio.on('connect')
def handle_connect():
    """WebSocket 接続"""
    system_stats["active_connections"] += 1
    logger.info(f"Client connected. Active connections: {system_stats['active_connections']}")
    
    # 初期状態を送信
    emit('system_status', {
        "qwq_engine": {"status": "running" if qwq_engine and qwq_engine.is_loaded else "stopped"},
        "mcp_server": {"status": "running" if mcp_server and mcp_server.is_running else "stopped"},
        "vscode_server": {"status": "running" if vscode_integration and vscode_integration.is_running else "stopped"},
        "git_manager": {"status": "active" if git_manager else "inactive"},
        "multi_agent": {"status": "running" if multi_agent_system and multi_agent_system.is_running else "stopped"}
    })

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket 切断"""
    system_stats["active_connections"] -= 1
    logger.info(f"Client disconnected. Active connections: {system_stats['active_connections']}")

@socketio.on('request_dashboard_data')
def handle_dashboard_request():
    """ダッシュボードデータ要求"""
    try:
        # リアルタイムメトリクス
        import psutil
        
        metrics = {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_io": 1.2,  # 仮の値
            "active_tasks": len(multi_agent_system.tasks) if multi_agent_system else 0,
            "completed_today": 24  # 仮の値
        }
        
        emit('realtime_metrics', metrics)
        
        # エージェント統計
        if multi_agent_system:
            agent_stats = {}
            for agent_id, agent in multi_agent_system.agents.items():
                agent_stats[agent_id] = {
                    "role": agent.role.value.upper(),
                    "tasks_completed": agent.performance_metrics["tasks_completed"],
                    "quality_score": agent.performance_metrics["quality_score"]
                }
            emit('agent_stats', agent_stats)
        
        # MCP統計
        if mcp_server:
            mcp_stats = mcp_server.stats.get_stats()
            emit('mcp_stats', mcp_stats)
        
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")

# ===== バックグラウンドタスク =====

def background_monitor():
    """バックグラウンド監視"""
    while True:
        try:
            # システム状態を定期的にブロードキャスト
            if system_stats["active_connections"] > 0:
                socketio.emit('system_heartbeat', {
                    "timestamp": datetime.now().isoformat(),
                    "uptime": time.time() - system_stats["start_time"]
                })
            
            time.sleep(30)  # 30秒間隔
            
        except Exception as e:
            logger.error(f"Background monitor error: {e}")
            time.sleep(60)

# ===== メインルート =====

@app.route('/')
def index():
    """メインページ"""
    return jsonify({
        "name": "AutoAI v3.0",
        "description": "完全自律型開発環境",
        "version": "3.0.0",
        "features": [
            "QwQ-32B ローカル推論",
            "MCP サーバー",
            "VSCode 統合",
            "Git 完全機能",
            "マルチエージェントシステム"
        ],
        "endpoints": {
            "health": "/api/health",
            "qwq": "/api/qwq/*",
            "mcp": "/api/mcp/*",
            "vscode": "/api/vscode/*",
            "git": "/api/git/*",
            "agents": "/api/agents/*",
            "system": "/api/system/*"
        }
    })

if __name__ == '__main__':
    # バックグラウンド監視スレッド開始
    monitor_thread = threading.Thread(target=background_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Flask アプリケーション開始
    logger.info("Starting AutoAI v3.0 server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

