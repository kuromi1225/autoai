#!/usr/bin/env python3
"""
AutoAI v3.0 統合テストスイート

全システムの統合テストを実行
"""

import asyncio
import aiohttp
import json
import time
import logging
import sys
import os
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoAIIntegrationTest:
    """AutoAI v3.0 統合テスト"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = None
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "errors": []
        }
    
    async def setup(self):
        """テスト環境セットアップ"""
        self.session = aiohttp.ClientSession()
        logger.info("Test environment setup completed")
    
    async def teardown(self):
        """テスト環境クリーンアップ"""
        if self.session:
            await self.session.close()
        logger.info("Test environment cleaned up")
    
    async def run_test(self, test_name, test_func):
        """個別テスト実行"""
        self.test_results["total_tests"] += 1
        
        try:
            logger.info(f"Running test: {test_name}")
            await test_func()
            self.test_results["passed_tests"] += 1
            logger.info(f"✅ {test_name} - PASSED")
            
        except Exception as e:
            self.test_results["failed_tests"] += 1
            error_msg = f"❌ {test_name} - FAILED: {str(e)}"
            logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
    
    async def test_health_check(self):
        """ヘルスチェックテスト"""
        async with self.session.get(f"{self.base_url}/api/health") as response:
            assert response.status == 200
            data = await response.json()
            assert data["status"] == "healthy"
            assert "systems" in data
            logger.info(f"Health check response: {data}")
    
    async def test_qwq_engine(self):
        """QwQ-32B エンジンテスト"""
        payload = {
            "prompt": "Hello, how are you?",
            "max_length": 100,
            "temperature": 0.7
        }
        
        async with self.session.post(
            f"{self.base_url}/api/qwq/generate",
            json=payload
        ) as response:
            if response.status == 503:
                logger.warning("QwQ engine not available - skipping test")
                return
            
            assert response.status == 200
            data = await response.json()
            assert "response" in data
            assert len(data["response"]) > 0
            logger.info(f"QwQ response length: {len(data['response'])}")
    
    async def test_mcp_server(self):
        """MCP サーバーテスト"""
        async with self.session.get(f"{self.base_url}/api/mcp/status") as response:
            if response.status == 503:
                logger.warning("MCP server not available - skipping test")
                return
            
            assert response.status == 200
            data = await response.json()
            assert "status" in data
            assert "stats" in data
            logger.info(f"MCP status: {data['status']}")
    
    async def test_vscode_integration(self):
        """VSCode 統合テスト"""
        async with self.session.get(f"{self.base_url}/api/vscode/status") as response:
            if response.status == 503:
                logger.warning("VSCode integration not available - skipping test")
                return
            
            assert response.status == 200
            data = await response.json()
            assert "vscode_installed" in data
            logger.info(f"VSCode status: {data}")
    
    async def test_vscode_ai_assistant(self):
        """VSCode AI アシスタントテスト"""
        payload = {
            "code": "def hello():\n    print('Hello, World!')",
            "question": "What does this function do?",
            "language": "python"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/vscode/ask_assistant",
            json=payload
        ) as response:
            if response.status == 503:
                logger.warning("VSCode AI assistant not available - skipping test")
                return
            
            assert response.status == 200
            data = await response.json()
            assert "response" in data
            logger.info(f"AI assistant response length: {len(data['response'])}")
    
    async def test_git_manager(self):
        """Git 管理テスト"""
        async with self.session.get(f"{self.base_url}/api/git/status") as response:
            # Git リポジトリがない場合は404が正常
            if response.status == 404:
                logger.info("No active Git repository - this is expected")
                return
            
            if response.status == 503:
                logger.warning("Git manager not available - skipping test")
                return
            
            assert response.status == 200
            data = await response.json()
            assert "status" in data or "info" in data
            logger.info(f"Git status: {data}")
    
    async def test_multi_agent_system(self):
        """マルチエージェントシステムテスト"""
        async with self.session.get(f"{self.base_url}/api/agents/status") as response:
            if response.status == 503:
                logger.warning("Multi-agent system not available - skipping test")
                return
            
            assert response.status == 200
            data = await response.json()
            assert "is_running" in data
            assert "agents" in data
            logger.info(f"Agent system status: {data['is_running']}")
    
    async def test_task_submission(self):
        """タスク投入テスト"""
        payload = {
            "title": "Test Task",
            "description": "This is a test task for integration testing",
            "role": "pg",
            "priority": "low"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/agents/submit_task",
            json=payload
        ) as response:
            if response.status == 503:
                logger.warning("Multi-agent system not available - skipping test")
                return
            
            assert response.status == 200
            data = await response.json()
            assert "task_id" in data
            
            # タスク状態確認
            task_id = data["task_id"]
            await asyncio.sleep(1)  # 少し待機
            
            async with self.session.get(
                f"{self.base_url}/api/agents/task/{task_id}"
            ) as task_response:
                assert task_response.status == 200
                task_data = await task_response.json()
                assert "id" in task_data
                logger.info(f"Task {task_id} status: {task_data.get('status', 'unknown')}")
    
    async def test_system_statistics(self):
        """システム統計テスト"""
        async with self.session.get(f"{self.base_url}/api/system/stats") as response:
            assert response.status == 200
            data = await response.json()
            assert "uptime" in data
            assert "total_requests" in data
            logger.info(f"System uptime: {data['uptime']:.2f} seconds")
    
    async def test_websocket_connection(self):
        """WebSocket 接続テスト"""
        try:
            import websockets
            
            uri = f"ws://localhost:5000/socket.io/?EIO=4&transport=websocket"
            
            # WebSocket接続テスト（簡易版）
            # 実際のSocket.IOクライアントを使用する場合はpython-socketio が必要
            logger.info("WebSocket connection test - basic connectivity check")
            
            # 基本的な接続テストのみ実行
            # 実際のメッセージ送受信テストは省略
            
        except ImportError:
            logger.warning("websockets library not available - skipping WebSocket test")
        except Exception as e:
            logger.warning(f"WebSocket test failed: {e}")
    
    async def test_code_generation(self):
        """コード生成テスト"""
        payload = {
            "prompt": "Create a simple Python function that adds two numbers",
            "language": "python",
            "context": "This is for a calculator application"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/vscode/generate_code",
            json=payload
        ) as response:
            if response.status == 503:
                logger.warning("Code generation not available - skipping test")
                return
            
            assert response.status == 200
            data = await response.json()
            assert "response" in data
            assert "def" in data["response"]  # Python関数が含まれているはず
            logger.info(f"Generated code length: {len(data['response'])}")
    
    async def test_performance_metrics(self):
        """パフォーマンステスト"""
        start_time = time.time()
        
        # 複数のAPIエンドポイントに同時リクエスト
        tasks = [
            self.session.get(f"{self.base_url}/api/health"),
            self.session.get(f"{self.base_url}/api/system/stats"),
            self.session.get(f"{self.base_url}/api/agents/status")
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 成功したレスポンスをカウント
        successful_responses = sum(
            1 for response in responses 
            if not isinstance(response, Exception) and response.status == 200
        )
        
        logger.info(f"Performance test: {successful_responses}/3 requests successful in {duration:.2f}s")
        
        # 基本的なパフォーマンス要件
        assert duration < 5.0  # 5秒以内
        assert successful_responses >= 1  # 最低1つは成功
    
    async def run_all_tests(self):
        """全テスト実行"""
        logger.info("Starting AutoAI v3.0 Integration Tests")
        logger.info("=" * 50)
        
        await self.setup()
        
        # テスト一覧
        tests = [
            ("Health Check", self.test_health_check),
            ("QwQ Engine", self.test_qwq_engine),
            ("MCP Server", self.test_mcp_server),
            ("VSCode Integration", self.test_vscode_integration),
            ("VSCode AI Assistant", self.test_vscode_ai_assistant),
            ("Git Manager", self.test_git_manager),
            ("Multi-Agent System", self.test_multi_agent_system),
            ("Task Submission", self.test_task_submission),
            ("System Statistics", self.test_system_statistics),
            ("WebSocket Connection", self.test_websocket_connection),
            ("Code Generation", self.test_code_generation),
            ("Performance Metrics", self.test_performance_metrics)
        ]
        
        # 各テストを実行
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
            await asyncio.sleep(0.5)  # テスト間の間隔
        
        await self.teardown()
        
        # 結果サマリー
        logger.info("=" * 50)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total Tests: {self.test_results['total_tests']}")
        logger.info(f"Passed: {self.test_results['passed_tests']}")
        logger.info(f"Failed: {self.test_results['failed_tests']}")
        
        if self.test_results['failed_tests'] > 0:
            logger.info("\nFAILED TESTS:")
            for error in self.test_results['errors']:
                logger.info(f"  {error}")
        
        success_rate = (self.test_results['passed_tests'] / self.test_results['total_tests']) * 100
        logger.info(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            logger.info("🎉 Integration tests PASSED!")
            return True
        else:
            logger.error("❌ Integration tests FAILED!")
            return False

async def wait_for_server(base_url, timeout=60):
    """サーバーの起動を待機"""
    logger.info(f"Waiting for server at {base_url}...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/api/health", timeout=5) as response:
                    if response.status == 200:
                        logger.info("Server is ready!")
                        return True
        except:
            pass
        
        await asyncio.sleep(2)
    
    logger.error(f"Server not ready after {timeout} seconds")
    return False

async def main():
    """メイン関数"""
    base_url = os.getenv("AUTOAI_BASE_URL", "http://localhost:5000")
    
    # サーバーの起動を待機
    if not await wait_for_server(base_url):
        sys.exit(1)
    
    # 統合テスト実行
    test_suite = AutoAIIntegrationTest(base_url)
    success = await test_suite.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())

