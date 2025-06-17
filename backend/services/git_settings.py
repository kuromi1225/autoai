"""
Complete Implementation of Git Settings Service

Git連携設定の完全実装
"""

import os
import json
import logging
import subprocess
import tempfile
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
import requests
from cryptography.fernet import Fernet

from services.secret_manager import get_secret_manager

logger = logging.getLogger(__name__)

class GitSettings:
    """Git設定管理クラス"""
    
    def __init__(self):
        self.secret_manager = get_secret_manager()
        self.settings_file = os.path.join(os.getcwd(), 'data', 'git_settings.json')
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """データディレクトリの存在を確認"""
        data_dir = os.path.dirname(self.settings_file)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, mode=0o700)
    
    def _load_settings(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        if not os.path.exists(self.settings_file):
            return {}
        
        try:
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load Git settings: {e}")
            return {}
    
    def _save_settings(self, settings: Dict[str, Any]) -> bool:
        """設定ファイルを保存"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            # ファイル権限を制限
            os.chmod(self.settings_file, 0o600)
            return True
            
        except Exception as e:
            logger.error(f"Failed to save Git settings: {e}")
            return False
    
    def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """ユーザーのGit設定を取得"""
        all_settings = self._load_settings()
        user_settings = all_settings.get(user_id, {})
        
        # デフォルト値を設定
        default_settings = {
            'repository_url': '',
            'branch': 'main',
            'username': '',
            'access_token': '',
            'auto_commit': True,
            'commit_message_template': 'Auto-commit by Devin AI: {task_description}',
            'is_configured': False
        }
        
        # 既存設定とデフォルト設定をマージ
        result = {**default_settings, **user_settings}
        
        # アクセストークンを復号化
        if result.get('access_token_encrypted'):
            try:
                result['access_token'] = self.secret_manager.decrypt_value(
                    result['access_token_encrypted']
                )
                # 暗号化されたトークンは除去
                del result['access_token_encrypted']
            except Exception as e:
                logger.error(f"Failed to decrypt access token: {e}")
                result['access_token'] = ''
        
        return result
    
    def save_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """ユーザーのGit設定を保存"""
        try:
            all_settings = self._load_settings()
            
            # アクセストークンを暗号化
            settings_to_save = settings.copy()
            if settings_to_save.get('access_token'):
                encrypted_token = self.secret_manager.encrypt_value(
                    settings_to_save['access_token']
                )
                settings_to_save['access_token_encrypted'] = encrypted_token
                # 平文のトークンは除去
                del settings_to_save['access_token']
            
            # 設定が有効かどうかを判定
            settings_to_save['is_configured'] = bool(
                settings.get('repository_url') and 
                settings.get('username') and 
                settings.get('access_token')
            )
            
            # タイムスタンプを追加
            settings_to_save['updated_at'] = datetime.utcnow().isoformat()
            
            all_settings[user_id] = settings_to_save
            
            return self._save_settings(all_settings)
            
        except Exception as e:
            logger.error(f"Failed to save user Git settings: {e}")
            return False
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Git設定の妥当性を検証"""
        errors = []
        warnings = []
        
        # 必須フィールドの確認
        required_fields = ['repository_url', 'username', 'access_token']
        for field in required_fields:
            if not settings.get(field):
                errors.append(f"'{field}' is required")
        
        # リポジトリURLの形式確認
        repo_url = settings.get('repository_url', '')
        if repo_url:
            try:
                parsed = urlparse(repo_url)
                if not parsed.scheme or not parsed.netloc:
                    errors.append("Invalid repository URL format")
                elif parsed.scheme not in ['http', 'https']:
                    warnings.append("HTTPS is recommended for repository URL")
            except Exception:
                errors.append("Invalid repository URL")
        
        # ブランチ名の確認
        branch = settings.get('branch', '')
        if branch and not self._is_valid_branch_name(branch):
            errors.append("Invalid branch name")
        
        # コミットメッセージテンプレートの確認
        commit_template = settings.get('commit_message_template', '')
        if commit_template and '{task_description}' not in commit_template:
            warnings.append("Commit message template should include {task_description} placeholder")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _is_valid_branch_name(self, branch_name: str) -> bool:
        """ブランチ名の妥当性を確認"""
        if not branch_name:
            return False
        
        # Git ブランチ名の基本的なルール
        invalid_chars = ['..', '~', '^', ':', '?', '*', '[', '\\', ' ']
        for char in invalid_chars:
            if char in branch_name:
                return False
        
        # 先頭と末尾の文字確認
        if branch_name.startswith('.') or branch_name.endswith('.'):
            return False
        if branch_name.startswith('/') or branch_name.endswith('/'):
            return False
        
        return True
    
    def test_connection(self, repository_url: str, username: str, access_token: str) -> Dict[str, Any]:
        """Git接続をテスト"""
        try:
            # URLの解析
            parsed = urlparse(repository_url)
            
            if 'github.com' in parsed.netloc:
                return self._test_github_connection(repository_url, username, access_token)
            elif 'gitlab.com' in parsed.netloc:
                return self._test_gitlab_connection(repository_url, username, access_token)
            else:
                return self._test_generic_git_connection(repository_url, username, access_token)
                
        except Exception as e:
            logger.error(f"Git connection test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'unknown'
            }
    
    def _test_github_connection(self, repository_url: str, username: str, access_token: str) -> Dict[str, Any]:
        """GitHub接続をテスト"""
        try:
            # リポジトリ情報を取得
            repo_path = repository_url.replace('https://github.com/', '').replace('.git', '')
            api_url = f"https://api.github.com/repos/{repo_path}"
            
            headers = {
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_info = response.json()
                return {
                    'success': True,
                    'provider': 'github',
                    'repository_name': repo_info.get('full_name'),
                    'private': repo_info.get('private', False),
                    'permissions': {
                        'push': repo_info.get('permissions', {}).get('push', False),
                        'pull': repo_info.get('permissions', {}).get('pull', False)
                    }
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': 'Invalid access token',
                    'provider': 'github'
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Repository not found or no access',
                    'provider': 'github'
                }
            else:
                return {
                    'success': False,
                    'error': f'GitHub API error: {response.status_code}',
                    'provider': 'github'
                }
                
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'provider': 'github'
            }
    
    def _test_gitlab_connection(self, repository_url: str, username: str, access_token: str) -> Dict[str, Any]:
        """GitLab接続をテスト"""
        try:
            # プロジェクトIDまたはパスを取得
            project_path = repository_url.replace('https://gitlab.com/', '').replace('.git', '')
            api_url = f"https://gitlab.com/api/v4/projects/{project_path.replace('/', '%2F')}"
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                project_info = response.json()
                return {
                    'success': True,
                    'provider': 'gitlab',
                    'repository_name': project_info.get('path_with_namespace'),
                    'private': project_info.get('visibility') == 'private'
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': 'Invalid access token',
                    'provider': 'gitlab'
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Project not found or no access',
                    'provider': 'gitlab'
                }
            else:
                return {
                    'success': False,
                    'error': f'GitLab API error: {response.status_code}',
                    'provider': 'gitlab'
                }
                
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'provider': 'gitlab'
            }
    
    def _test_generic_git_connection(self, repository_url: str, username: str, access_token: str) -> Dict[str, Any]:
        """汎用Git接続をテスト"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 認証情報を含むURLを構築
                parsed = urlparse(repository_url)
                auth_url = f"{parsed.scheme}://{username}:{access_token}@{parsed.netloc}{parsed.path}"
                
                # git ls-remote でリモートリポジトリの存在確認
                result = subprocess.run(
                    ['git', 'ls-remote', auth_url],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    return {
                        'success': True,
                        'provider': 'generic',
                        'repository_url': repository_url
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Git command failed: {result.stderr}',
                        'provider': 'generic'
                    }
                    
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Connection timeout',
                'provider': 'generic'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'generic'
            }
    
    def commit_and_push(self, user_id: str, file_paths: list, task_description: str) -> Dict[str, Any]:
        """ファイルをコミットしてプッシュ"""
        try:
            settings = self.get_user_settings(user_id)
            
            if not settings.get('is_configured'):
                return {
                    'success': False,
                    'error': 'Git settings not configured'
                }
            
            if not settings.get('auto_commit'):
                return {
                    'success': False,
                    'error': 'Auto-commit is disabled'
                }
            
            # コミットメッセージを生成
            commit_message = settings['commit_message_template'].format(
                task_description=task_description,
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )
            
            # Git操作を実行
            return self._execute_git_operations(settings, file_paths, commit_message)
            
        except Exception as e:
            logger.error(f"Failed to commit and push: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_git_operations(self, settings: Dict[str, Any], file_paths: list, commit_message: str) -> Dict[str, Any]:
        """Git操作を実行"""
        try:
            # 認証情報を含むURLを構築
            parsed = urlparse(settings['repository_url'])
            auth_url = f"{parsed.scheme}://{settings['username']}:{settings['access_token']}@{parsed.netloc}{parsed.path}"
            
            # 作業ディレクトリ
            work_dir = os.getcwd()
            
            # Git設定
            subprocess.run(['git', 'config', 'user.name', settings['username']], cwd=work_dir, check=True)
            subprocess.run(['git', 'config', 'user.email', f"{settings['username']}@devin-ai-clone.local"], cwd=work_dir, check=True)
            
            # リモートリポジトリを設定（存在しない場合）
            try:
                subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=work_dir, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                subprocess.run(['git', 'remote', 'add', 'origin', auth_url], cwd=work_dir, check=True)
            
            # ファイルを追加
            for file_path in file_paths:
                if os.path.exists(file_path):
                    subprocess.run(['git', 'add', file_path], cwd=work_dir, check=True)
            
            # コミット
            subprocess.run(['git', 'commit', '-m', commit_message], cwd=work_dir, check=True)
            
            # プッシュ
            subprocess.run(['git', 'push', 'origin', settings['branch']], cwd=work_dir, check=True)
            
            return {
                'success': True,
                'commit_message': commit_message,
                'files_committed': file_paths,
                'branch': settings['branch']
            }
            
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f'Git command failed: {e}',
                'command': ' '.join(e.cmd) if hasattr(e, 'cmd') else 'unknown'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

