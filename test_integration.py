#!/usr/bin/env python3
"""
統合テストスクリプト

このスクリプトは、AutoAIシステムの全機能をテストします。
"""

import sys
import os
import time
import requests
import json
import logging
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoAITester:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.user_id = None
    
    def test_health_check(self):
        """ヘルスチェックテスト"""
        logger.info("Testing health check...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            logger.info("✅ Health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
    
    def test_system_info(self):
        """システム情報テスト"""
        logger.info("Testing system info...")
        try:
            response = self.session.get(f"{self.base_url}/api/system/info")
            assert response.status_code == 200
            data = response.json()
            assert 'version' in data
            assert 'features' in data
            assert 'tools' in data
            logger.info("✅ System info test passed")
            return True
        except Exception as e:
            logger.error(f"❌ System info test failed: {e}")
            return False
    
    def test_user_registration(self):
        """ユーザー登録テスト"""
        logger.info("Testing user registration...")
        try:
            test_user = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpassword123'
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=test_user
            )
            
            if response.status_code == 201:
                data = response.json()
                assert data['success'] == True
                logger.info("✅ User registration passed")
                return True
            elif response.status_code == 400:
                # ユーザーが既に存在する場合
                logger.info("✅ User already exists (expected)")
                return True
            else:
                logger.error(f"❌ Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ User registration failed: {e}")
            return False
    
    def test_user_login(self):
        """ユーザーログインテスト"""
        logger.info("Testing user login...")
        try:
            login_data = {
                'username': 'testuser',
                'password': 'testpassword123'
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            assert 'token' in data
            
            self.token = data['token']
            self.user_id = data['user']['id']
            
            # 認証ヘッダーを設定
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            
            logger.info("✅ User login passed")
            return True
        except Exception as e:
            logger.error(f"❌ User login failed: {e}")
            return False
    
    def test_workspace_files(self):
        """ワークスペースファイルテスト"""
        logger.info("Testing workspace files...")
        try:
            # ファイル一覧取得
            response = self.session.get(f"{self.base_url}/api/workspace/files")
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            
            # テストファイル作成
            test_file_data = {
                'path': 'test_file.txt',
                'content': 'This is a test file content.'
            }
            
            response = self.session.post(
                f"{self.base_url}/api/workspace/file",
                json=test_file_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            
            # ファイル読み込み
            response = self.session.get(f"{self.base_url}/api/workspace/file/test_file.txt")
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            assert data['content'] == test_file_data['content']
            
            # ファイル削除
            response = self.session.delete(f"{self.base_url}/api/workspace/file/test_file.txt")
            assert response.status_code == 200
            
            logger.info("✅ Workspace files test passed")
            return True
        except Exception as e:
            logger.error(f"❌ Workspace files test failed: {e}")
            return False
    
    def test_project_management(self):
        """プロジェクト管理テスト"""
        logger.info("Testing project management...")
        try:
            # プロジェクト作成
            project_data = {
                'name': 'test_project',
                'description': 'Test project for integration testing',
                'template': 'python'
            }
            
            response = self.session.post(
                f"{self.base_url}/api/workspace/projects",
                json=project_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            
            # プロジェクト一覧取得
            response = self.session.get(f"{self.base_url}/api/workspace/projects")
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            assert len(data['projects']) > 0
            
            # プロジェクト取得
            response = self.session.get(f"{self.base_url}/api/workspace/projects/test_project")
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            assert data['project']['name'] == 'test_project'
            
            # プロジェクト削除
            response = self.session.delete(f"{self.base_url}/api/workspace/projects/test_project")
            assert response.status_code == 200
            
            logger.info("✅ Project management test passed")
            return True
        except Exception as e:
            logger.error(f"❌ Project management test failed: {e}")
            return False
    
    def test_chat_message(self):
        """チャットメッセージテスト"""
        logger.info("Testing chat message...")
        try:
            message_data = {
                'message': 'Hello, this is a test message.',
                'session_id': 'test_session_123'
            }
            
            response = self.session.post(
                f"{self.base_url}/api/chat/message",
                json=message_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            
            logger.info("✅ Chat message test passed")
            return True
        except Exception as e:
            logger.error(f"❌ Chat message test failed: {e}")
            return False
    
    def test_tool_execution(self):
        """ツール実行テスト"""
        logger.info("Testing tool execution...")
        try:
            tool_data = {
                'tool_name': 'file_editor',
                'parameters': {
                    'action': 'write',
                    'file_path': 'test_tool_file.txt',
                    'content': 'This file was created by tool execution test.'
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/tools/execute",
                json=tool_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data['success'] == True
            
            logger.info("✅ Tool execution test passed")
            return True
        except Exception as e:
            logger.error(f"❌ Tool execution test failed: {e}")
            return False
    
    def run_all_tests(self):
        """全テストを実行"""
        logger.info("Starting AutoAI integration tests...")
        
        tests = [
            self.test_health_check,
            self.test_system_info,
            self.test_user_registration,
            self.test_user_login,
            self.test_workspace_files,
            self.test_project_management,
            self.test_chat_message,
            self.test_tool_execution
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Test {test.__name__} crashed: {e}")
                failed += 1
            
            time.sleep(1)  # テスト間の間隔
        
        logger.info(f"\n=== Test Results ===")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total: {passed + failed}")
        
        if failed == 0:
            logger.info("🎉 All tests passed!")
            return True
        else:
            logger.error(f"💥 {failed} tests failed!")
            return False

def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = 'http://localhost:5000'
    
    logger.info(f"Testing AutoAI at {base_url}")
    
    tester = AutoAITester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

