"""
Model Context Protocol (MCP) サーバー実装

MCPプロトコルに準拠したサーバーで、AIモデルとツールの統合を提供
リアルタイム監視、プラグインシステム、パフォーマンス計測機能付き
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
import threading
from datetime import datetime
import psutil
import traceback

logger = logging.getLogger(__name__)

class MCPMessageType(Enum):
    """MCPメッセージタイプ"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"

@dataclass
class MCPMessage:
    """MCPメッセージ"""
    id: Optional[str]
    type: MCPMessageType
    method: Optional[str]
    params: Optional[Dict[str, Any]]
    result: Optional[Any]
    error: Optional[Dict[str, Any]]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = {
            "jsonrpc": "2.0",
            "id": self.id,
            "timestamp": self.timestamp
        }
        
        if self.type == MCPMessageType.REQUEST:
            data["method"] = self.method
            data["params"] = self.params or {}
        elif self.type == MCPMessageType.RESPONSE:
            if self.error:
                data["error"] = self.error
            else:
                data["result"] = self.result
        elif self.type == MCPMessageType.NOTIFICATION:
            data["method"] = self.method
            data["params"] = self.params or {}
            del data["id"]  # 通知にはIDなし
        
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """辞書からMCPメッセージを作成"""
        msg_id = data.get("id")
        timestamp = data.get("timestamp", time.time())
        
        if "method" in data and "id" in data:
            # リクエスト
            return cls(
                id=msg_id,
                type=MCPMessageType.REQUEST,
                method=data["method"],
                params=data.get("params"),
                result=None,
                error=None,
                timestamp=timestamp
            )
        elif "result" in data or "error" in data:
            # レスポンス
            return cls(
                id=msg_id,
                type=MCPMessageType.RESPONSE,
                method=None,
                params=None,
                result=data.get("result"),
                error=data.get("error"),
                timestamp=timestamp
            )
        elif "method" in data:
            # 通知
            return cls(
                id=None,
                type=MCPMessageType.NOTIFICATION,
                method=data["method"],
                params=data.get("params"),
                result=None,
                error=None,
                timestamp=timestamp
            )
        else:
            raise ValueError("Invalid MCP message format")

@dataclass
class MCPTool:
    """MCPツール定義"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    category: str = "general"
    version: str = "1.0.0"
    enabled: bool = True

@dataclass
class MCPResource:
    """MCPリソース定義"""
    uri: str
    name: str
    description: str
    mime_type: str
    handler: Callable

class MCPServerStats:
    """MCPサーバー統計"""
    
    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.total_responses = 0
        self.total_notifications = 0
        self.total_errors = 0
        self.active_connections = 0
        self.request_times = []
        self.error_log = []
    
    def record_request(self, duration: float):
        """リクエスト記録"""
        self.total_requests += 1
        self.request_times.append(duration)
        # 最新1000件のみ保持
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]
    
    def record_response(self):
        """レスポンス記録"""
        self.total_responses += 1
    
    def record_notification(self):
        """通知記録"""
        self.total_notifications += 1
    
    def record_error(self, error: str):
        """エラー記録"""
        self.total_errors += 1
        self.error_log.append({
            "timestamp": time.time(),
            "error": error
        })
        # 最新100件のみ保持
        if len(self.error_log) > 100:
            self.error_log = self.error_log[-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        uptime = time.time() - self.start_time
        avg_request_time = sum(self.request_times) / len(self.request_times) if self.request_times else 0
        
        return {
            "uptime": uptime,
            "total_requests": self.total_requests,
            "total_responses": self.total_responses,
            "total_notifications": self.total_notifications,
            "total_errors": self.total_errors,
            "active_connections": self.active_connections,
            "average_request_time": avg_request_time,
            "requests_per_second": self.total_requests / uptime if uptime > 0 else 0,
            "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            "recent_errors": self.error_log[-10:]  # 最新10件のエラー
        }

class MCPServer:
    """Model Context Protocol サーバー"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.stats = MCPServerStats()
        self.is_running = False
        self.server = None
        
        # プラグインシステム
        self.plugins: Dict[str, Any] = {}
        self.middleware: List[Callable] = []
        
        # 監視システム
        self.monitor_thread = None
        self.monitor_interval = 5.0  # 5秒間隔
        
        # 標準ツールを登録
        self._register_standard_tools()
    
    def _register_standard_tools(self):
        """標準ツールを登録"""
        
        # サーバー情報取得ツール
        self.register_tool(MCPTool(
            name="server_info",
            description="Get MCP server information and statistics",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._handle_server_info,
            category="system"
        ))
        
        # ツール一覧取得ツール
        self.register_tool(MCPTool(
            name="list_tools",
            description="List all available tools",
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category"
                    }
                },
                "required": []
            },
            handler=self._handle_list_tools,
            category="system"
        ))
        
        # ヘルスチェックツール
        self.register_tool(MCPTool(
            name="health_check",
            description="Perform server health check",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._handle_health_check,
            category="system"
        ))
    
    def register_tool(self, tool: MCPTool):
        """ツールを登録"""
        self.tools[tool.name] = tool
        logger.info(f"Registered MCP tool: {tool.name}")
    
    def unregister_tool(self, name: str):
        """ツールを登録解除"""
        if name in self.tools:
            del self.tools[name]
            logger.info(f"Unregistered MCP tool: {name}")
    
    def register_resource(self, resource: MCPResource):
        """リソースを登録"""
        self.resources[resource.uri] = resource
        logger.info(f"Registered MCP resource: {resource.uri}")
    
    def register_plugin(self, name: str, plugin: Any):
        """プラグインを登録"""
        self.plugins[name] = plugin
        logger.info(f"Registered MCP plugin: {name}")
        
        # プラグインのツールを自動登録
        if hasattr(plugin, 'get_tools'):
            for tool in plugin.get_tools():
                self.register_tool(tool)
    
    def add_middleware(self, middleware: Callable):
        """ミドルウェアを追加"""
        self.middleware.append(middleware)
    
    async def start(self):
        """サーバー開始"""
        logger.info(f"Starting MCP server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        )
        
        self.is_running = True
        
        # 監視スレッド開始
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("MCP server started successfully")
    
    async def stop(self):
        """サーバー停止"""
        logger.info("Stopping MCP server")
        
        self.is_running = False
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # 全クライアント切断
        for client_id, websocket in self.clients.items():
            await websocket.close()
        
        self.clients.clear()
        logger.info("MCP server stopped")
    
    async def _handle_client(self, websocket, path):
        """クライアント接続処理"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        self.stats.active_connections += 1
        
        logger.info(f"Client connected: {client_id}")
        
        try:
            async for message in websocket:
                await self._process_message(client_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            self.stats.active_connections -= 1
    
    async def _process_message(self, client_id: str, raw_message: str):
        """メッセージ処理"""
        start_time = time.time()
        
        try:
            # JSON解析
            data = json.loads(raw_message)
            message = MCPMessage.from_dict(data)
            
            # ミドルウェア実行
            for middleware in self.middleware:
                message = await self._run_middleware(middleware, message)
                if message is None:
                    return  # ミドルウェアでブロックされた
            
            # メッセージタイプ別処理
            if message.type == MCPMessageType.REQUEST:
                await self._handle_request(client_id, message)
            elif message.type == MCPMessageType.NOTIFICATION:
                await self._handle_notification(client_id, message)
                self.stats.record_notification()
            
            # 統計更新
            duration = time.time() - start_time
            self.stats.record_request(duration)
            
        except json.JSONDecodeError as e:
            await self._send_error(client_id, None, -32700, "Parse error", str(e))
            self.stats.record_error(f"Parse error: {e}")
        except Exception as e:
            await self._send_error(client_id, None, -32603, "Internal error", str(e))
            self.stats.record_error(f"Internal error: {e}")
            logger.error(f"Error processing message: {e}\n{traceback.format_exc()}")
    
    async def _handle_request(self, client_id: str, message: MCPMessage):
        """リクエスト処理"""
        method = message.method
        params = message.params or {}
        
        try:
            if method == "tools/call":
                # ツール実行
                tool_name = params.get("name")
                tool_params = params.get("arguments", {})
                
                if tool_name not in self.tools:
                    await self._send_error(
                        client_id, message.id, -32601, 
                        "Method not found", f"Tool '{tool_name}' not found"
                    )
                    return
                
                tool = self.tools[tool_name]
                if not tool.enabled:
                    await self._send_error(
                        client_id, message.id, -32601,
                        "Tool disabled", f"Tool '{tool_name}' is disabled"
                    )
                    return
                
                # ツール実行
                result = await self._execute_tool(tool, tool_params)
                await self._send_response(client_id, message.id, result)
                
            elif method == "resources/read":
                # リソース読み取り
                uri = params.get("uri")
                
                if uri not in self.resources:
                    await self._send_error(
                        client_id, message.id, -32601,
                        "Resource not found", f"Resource '{uri}' not found"
                    )
                    return
                
                resource = self.resources[uri]
                result = await self._read_resource(resource, params)
                await self._send_response(client_id, message.id, result)
                
            elif method == "tools/list":
                # ツール一覧
                tools_list = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.parameters,
                        "category": tool.category,
                        "version": tool.version,
                        "enabled": tool.enabled
                    }
                    for tool in self.tools.values()
                ]
                await self._send_response(client_id, message.id, {"tools": tools_list})
                
            elif method == "resources/list":
                # リソース一覧
                resources_list = [
                    {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mimeType": resource.mime_type
                    }
                    for resource in self.resources.values()
                ]
                await self._send_response(client_id, message.id, {"resources": resources_list})
                
            else:
                await self._send_error(
                    client_id, message.id, -32601,
                    "Method not found", f"Method '{method}' not supported"
                )
                
        except Exception as e:
            await self._send_error(
                client_id, message.id, -32603,
                "Internal error", str(e)
            )
            logger.error(f"Error handling request {method}: {e}")
    
    async def _handle_notification(self, client_id: str, message: MCPMessage):
        """通知処理"""
        method = message.method
        params = message.params or {}
        
        logger.info(f"Received notification: {method} from {client_id}")
        
        # 通知の処理（必要に応じて実装）
        if method == "initialized":
            logger.info(f"Client {client_id} initialized")
        elif method == "cancelled":
            logger.info(f"Request cancelled by client {client_id}")
    
    async def _execute_tool(self, tool: MCPTool, params: Dict[str, Any]) -> Any:
        """ツール実行"""
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                return await tool.handler(params)
            else:
                return tool.handler(params)
        except Exception as e:
            logger.error(f"Error executing tool {tool.name}: {e}")
            raise
    
    async def _read_resource(self, resource: MCPResource, params: Dict[str, Any]) -> Any:
        """リソース読み取り"""
        try:
            if asyncio.iscoroutinefunction(resource.handler):
                return await resource.handler(params)
            else:
                return resource.handler(params)
        except Exception as e:
            logger.error(f"Error reading resource {resource.uri}: {e}")
            raise
    
    async def _run_middleware(self, middleware: Callable, message: MCPMessage) -> Optional[MCPMessage]:
        """ミドルウェア実行"""
        try:
            if asyncio.iscoroutinefunction(middleware):
                return await middleware(message)
            else:
                return middleware(message)
        except Exception as e:
            logger.error(f"Error in middleware: {e}")
            return message
    
    async def _send_response(self, client_id: str, message_id: str, result: Any):
        """レスポンス送信"""
        response = MCPMessage(
            id=message_id,
            type=MCPMessageType.RESPONSE,
            method=None,
            params=None,
            result=result,
            error=None,
            timestamp=time.time()
        )
        
        await self._send_message(client_id, response)
        self.stats.record_response()
    
    async def _send_error(self, client_id: str, message_id: Optional[str], 
                         code: int, message: str, data: Optional[str] = None):
        """エラー送信"""
        error_data = {
            "code": code,
            "message": message
        }
        if data:
            error_data["data"] = data
        
        response = MCPMessage(
            id=message_id,
            type=MCPMessageType.RESPONSE,
            method=None,
            params=None,
            result=None,
            error=error_data,
            timestamp=time.time()
        )
        
        await self._send_message(client_id, response)
        self.stats.record_error(f"{code}: {message}")
    
    async def _send_message(self, client_id: str, message: MCPMessage):
        """メッセージ送信"""
        if client_id not in self.clients:
            logger.warning(f"Client {client_id} not found")
            return
        
        try:
            websocket = self.clients[client_id]
            data = json.dumps(message.to_dict())
            await websocket.send(data)
        except Exception as e:
            logger.error(f"Error sending message to {client_id}: {e}")
    
    async def broadcast_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """全クライアントに通知をブロードキャスト"""
        notification = MCPMessage(
            id=None,
            type=MCPMessageType.NOTIFICATION,
            method=method,
            params=params,
            result=None,
            error=None,
            timestamp=time.time()
        )
        
        for client_id in list(self.clients.keys()):
            await self._send_message(client_id, notification)
    
    def _monitor_loop(self):
        """監視ループ"""
        while self.is_running:
            try:
                stats = self.stats.get_stats()
                logger.debug(f"MCP Server Stats: {stats}")
                
                # 必要に応じて監視データを処理
                # 例: メトリクス送信、アラート、ログ出力など
                
                time.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(self.monitor_interval)
    
    # 標準ツールハンドラー
    def _handle_server_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """サーバー情報取得"""
        return {
            "name": "AutoAI MCP Server",
            "version": "3.0.0",
            "description": "Model Context Protocol server for AutoAI",
            "capabilities": {
                "tools": True,
                "resources": True,
                "notifications": True,
                "monitoring": True
            },
            "stats": self.stats.get_stats(),
            "tools_count": len(self.tools),
            "resources_count": len(self.resources),
            "plugins_count": len(self.plugins)
        }
    
    def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ツール一覧取得"""
        category_filter = params.get("category")
        
        tools = []
        for tool in self.tools.values():
            if category_filter and tool.category != category_filter:
                continue
            
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "version": tool.version,
                "enabled": tool.enabled,
                "parameters": tool.parameters
            })
        
        return {"tools": tools}
    
    def _handle_health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ヘルスチェック"""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": time.time() - self.stats.start_time,
            "active_connections": self.stats.active_connections,
            "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024
        }


# グローバルMCPサーバーインスタンス
_mcp_server = None

def get_mcp_server() -> MCPServer:
    """MCPサーバーのシングルトンインスタンス取得"""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server

async def start_mcp_server(host: str = "localhost", port: int = 8765) -> MCPServer:
    """MCPサーバー開始"""
    global _mcp_server
    _mcp_server = MCPServer(host, port)
    await _mcp_server.start()
    return _mcp_server

async def stop_mcp_server():
    """MCPサーバー停止"""
    global _mcp_server
    if _mcp_server:
        await _mcp_server.stop()
        _mcp_server = None

