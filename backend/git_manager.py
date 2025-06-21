"""
Git完全機能システム

ブランチ操作、プル/プッシュ/コミット、競合解決、自動化機能を提供
AI支援によるコミットメッセージ生成、コードレビュー統合
"""

import os
import git
import logging
import asyncio
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import json
import re
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class GitOperationType(Enum):
    """Git操作タイプ"""
    CLONE = "clone"
    PULL = "pull"
    PUSH = "push"
    COMMIT = "commit"
    BRANCH = "branch"
    MERGE = "merge"
    REBASE = "rebase"
    STASH = "stash"
    TAG = "tag"
    REMOTE = "remote"

@dataclass
class GitBranch:
    """Gitブランチ情報"""
    name: str
    is_current: bool
    is_remote: bool
    last_commit: str
    last_commit_message: str
    last_commit_date: str
    ahead: int = 0
    behind: int = 0

@dataclass
class GitCommit:
    """Gitコミット情報"""
    hash: str
    message: str
    author: str
    date: str
    files_changed: List[str]
    insertions: int
    deletions: int

@dataclass
class GitStatus:
    """Git状態情報"""
    branch: str
    is_clean: bool
    staged_files: List[str]
    modified_files: List[str]
    untracked_files: List[str]
    conflicted_files: List[str]
    ahead: int
    behind: int

@dataclass
class GitRemote:
    """Gitリモート情報"""
    name: str
    url: str
    fetch_url: str
    push_url: str

class GitManager:
    """Git管理システム"""
    
    def __init__(self, workspace_root: str = "/tmp/autoai_workspace"):
        self.workspace_root = Path(workspace_root)
        self.repos: Dict[str, git.Repo] = {}
        self.current_repo_path = None
        
        # AI機能
        self.ai_commit_messages = True
        self.ai_code_review = True
        self.auto_conflict_resolution = True
        
        # 設定
        self.config = {
            "user_name": "AutoAI Agent",
            "user_email": "autoai@example.com",
            "default_branch": "main",
            "auto_push": False,
            "auto_pull": True,
            "commit_template": True,
            "sign_commits": False
        }
        
        # 操作履歴
        self.operation_history = []
        
        # コミットテンプレート
        self.commit_templates = {
            "feat": "feat: add new feature",
            "fix": "fix: resolve bug",
            "docs": "docs: update documentation",
            "style": "style: format code",
            "refactor": "refactor: improve code structure",
            "test": "test: add or update tests",
            "chore": "chore: maintenance tasks"
        }
    
    def set_current_repo(self, repo_path: str) -> bool:
        """現在のリポジトリを設定"""
        try:
            repo_path = Path(repo_path).resolve()
            
            if repo_path in self.repos:
                self.current_repo_path = repo_path
                return True
            
            # 新しいリポジトリを開く
            if (repo_path / ".git").exists():
                repo = git.Repo(repo_path)
                self.repos[repo_path] = repo
                self.current_repo_path = repo_path
                logger.info(f"Set current repository: {repo_path}")
                return True
            else:
                logger.error(f"Not a git repository: {repo_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting current repository: {e}")
            return False
    
    def get_current_repo(self) -> Optional[git.Repo]:
        """現在のリポジトリを取得"""
        if self.current_repo_path and self.current_repo_path in self.repos:
            return self.repos[self.current_repo_path]
        return None
    
    async def clone_repository(self, url: str, local_path: Optional[str] = None, 
                              branch: Optional[str] = None) -> bool:
        """リポジトリをクローン"""
        try:
            if local_path is None:
                repo_name = url.split('/')[-1].replace('.git', '')
                local_path = self.workspace_root / repo_name
            else:
                local_path = Path(local_path)
            
            logger.info(f"Cloning repository: {url} to {local_path}")
            
            # クローン実行
            clone_kwargs = {}
            if branch:
                clone_kwargs['branch'] = branch
            
            repo = git.Repo.clone_from(url, local_path, **clone_kwargs)
            
            # リポジトリを登録
            self.repos[local_path] = repo
            self.current_repo_path = local_path
            
            # Git設定
            await self._configure_repo(repo)
            
            # 操作履歴記録
            self._record_operation(GitOperationType.CLONE, {
                "url": url,
                "local_path": str(local_path),
                "branch": branch
            })
            
            logger.info(f"Repository cloned successfully: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            return False
    
    async def _configure_repo(self, repo: git.Repo):
        """リポジトリを設定"""
        try:
            # ユーザー設定
            with repo.config_writer() as config:
                config.set_value("user", "name", self.config["user_name"])
                config.set_value("user", "email", self.config["user_email"])
                
                if self.config["sign_commits"]:
                    config.set_value("commit", "gpgsign", "true")
            
            logger.info("Repository configured successfully")
            
        except Exception as e:
            logger.error(f"Error configuring repository: {e}")
    
    def get_status(self) -> Optional[GitStatus]:
        """Git状態を取得"""
        repo = self.get_current_repo()
        if not repo:
            return None
        
        try:
            # ブランチ情報
            current_branch = repo.active_branch.name
            
            # ファイル状態
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]
            modified_files = [item.a_path for item in repo.index.diff(None)]
            untracked_files = repo.untracked_files
            
            # 競合ファイル
            conflicted_files = []
            try:
                conflicted_files = [item.a_path for item in repo.index.diff(None) 
                                  if item.change_type == 'U']
            except:
                pass
            
            # リモート追跡情報
            ahead, behind = 0, 0
            try:
                if repo.active_branch.tracking_branch():
                    ahead, behind = repo.iter_commits(
                        f'{repo.active_branch.tracking_branch()}..{current_branch}'
                    ), repo.iter_commits(
                        f'{current_branch}..{repo.active_branch.tracking_branch()}'
                    )
                    ahead = len(list(ahead))
                    behind = len(list(behind))
            except:
                pass
            
            is_clean = (len(staged_files) == 0 and len(modified_files) == 0 and 
                       len(untracked_files) == 0 and len(conflicted_files) == 0)
            
            return GitStatus(
                branch=current_branch,
                is_clean=is_clean,
                staged_files=staged_files,
                modified_files=modified_files,
                untracked_files=untracked_files,
                conflicted_files=conflicted_files,
                ahead=ahead,
                behind=behind
            )
            
        except Exception as e:
            logger.error(f"Error getting git status: {e}")
            return None
    
    def get_branches(self, include_remote: bool = True) -> List[GitBranch]:
        """ブランチ一覧を取得"""
        repo = self.get_current_repo()
        if not repo:
            return []
        
        branches = []
        
        try:
            # ローカルブランチ
            for branch in repo.branches:
                is_current = branch == repo.active_branch
                last_commit = branch.commit
                
                branches.append(GitBranch(
                    name=branch.name,
                    is_current=is_current,
                    is_remote=False,
                    last_commit=last_commit.hexsha[:8],
                    last_commit_message=last_commit.message.strip(),
                    last_commit_date=datetime.fromtimestamp(last_commit.committed_date).isoformat()
                ))
            
            # リモートブランチ
            if include_remote:
                for remote in repo.remotes:
                    for ref in remote.refs:
                        if ref.name.endswith('/HEAD'):
                            continue
                        
                        branch_name = ref.name.replace(f'{remote.name}/', '')
                        last_commit = ref.commit
                        
                        branches.append(GitBranch(
                            name=f"{remote.name}/{branch_name}",
                            is_current=False,
                            is_remote=True,
                            last_commit=last_commit.hexsha[:8],
                            last_commit_message=last_commit.message.strip(),
                            last_commit_date=datetime.fromtimestamp(last_commit.committed_date).isoformat()
                        ))
            
            return branches
            
        except Exception as e:
            logger.error(f"Error getting branches: {e}")
            return []
    
    async def create_branch(self, branch_name: str, from_branch: Optional[str] = None) -> bool:
        """ブランチを作成"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            # 作成元ブランチ
            if from_branch:
                start_point = repo.heads[from_branch]
            else:
                start_point = repo.active_branch
            
            # ブランチ作成
            new_branch = repo.create_head(branch_name, start_point)
            
            logger.info(f"Created branch: {branch_name}")
            
            # 操作履歴記録
            self._record_operation(GitOperationType.BRANCH, {
                "action": "create",
                "branch_name": branch_name,
                "from_branch": from_branch or repo.active_branch.name
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return False
    
    async def switch_branch(self, branch_name: str) -> bool:
        """ブランチを切り替え"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            # ブランチ存在確認
            if branch_name in [b.name for b in repo.branches]:
                branch = repo.heads[branch_name]
            elif branch_name.startswith('origin/'):
                # リモートブランチの場合、ローカルブランチを作成
                remote_branch = repo.remotes.origin.refs[branch_name.replace('origin/', '')]
                branch = repo.create_head(branch_name.replace('origin/', ''), remote_branch)
                branch.set_tracking_branch(remote_branch)
            else:
                logger.error(f"Branch not found: {branch_name}")
                return False
            
            # ブランチ切り替え
            branch.checkout()
            
            logger.info(f"Switched to branch: {branch_name}")
            
            # 操作履歴記録
            self._record_operation(GitOperationType.BRANCH, {
                "action": "switch",
                "branch_name": branch_name
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error switching branch: {e}")
            return False
    
    async def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """ブランチを削除"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            if branch_name == repo.active_branch.name:
                logger.error("Cannot delete current branch")
                return False
            
            if branch_name not in [b.name for b in repo.branches]:
                logger.error(f"Branch not found: {branch_name}")
                return False
            
            # ブランチ削除
            repo.delete_head(branch_name, force=force)
            
            logger.info(f"Deleted branch: {branch_name}")
            
            # 操作履歴記録
            self._record_operation(GitOperationType.BRANCH, {
                "action": "delete",
                "branch_name": branch_name,
                "force": force
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting branch: {e}")
            return False
    
    async def commit_changes(self, message: Optional[str] = None, 
                           files: Optional[List[str]] = None,
                           auto_stage: bool = True) -> bool:
        """変更をコミット"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            # ファイルをステージング
            if auto_stage:
                if files:
                    repo.index.add(files)
                else:
                    repo.git.add(A=True)  # すべてのファイルを追加
            
            # コミットメッセージ生成
            if not message:
                message = await self._generate_commit_message()
            
            # コミット実行
            commit = repo.index.commit(message)
            
            logger.info(f"Committed changes: {commit.hexsha[:8]} - {message}")
            
            # 操作履歴記録
            self._record_operation(GitOperationType.COMMIT, {
                "commit_hash": commit.hexsha,
                "message": message,
                "files": files or "all"
            })
            
            # 自動プッシュ
            if self.config["auto_push"]:
                await self.push_changes()
            
            return True
            
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            return False
    
    async def _generate_commit_message(self) -> str:
        """AIによるコミットメッセージ生成"""
        if not self.ai_commit_messages:
            return "Auto-generated commit message"
        
        repo = self.get_current_repo()
        if not repo:
            return "Auto-generated commit message"
        
        try:
            # 変更されたファイルを分析
            diff = repo.git.diff('--cached', '--name-status')
            if not diff:
                diff = repo.git.diff('--name-status')
            
            # ファイル変更の分析
            changes = self._analyze_changes(diff)
            
            # コミットメッセージ生成
            message = self._create_commit_message(changes)
            
            return message
            
        except Exception as e:
            logger.error(f"Error generating commit message: {e}")
            return "Auto-generated commit message"
    
    def _analyze_changes(self, diff_output: str) -> Dict[str, Any]:
        """変更内容を分析"""
        changes = {
            "added": [],
            "modified": [],
            "deleted": [],
            "file_types": set(),
            "categories": set()
        }
        
        for line in diff_output.split('\n'):
            if not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 2:
                status = parts[0]
                file_path = parts[1]
                
                # ファイルタイプ
                ext = Path(file_path).suffix.lower()
                if ext:
                    changes["file_types"].add(ext)
                
                # カテゴリ分類
                if any(keyword in file_path.lower() for keyword in ['test', 'spec']):
                    changes["categories"].add("test")
                elif any(keyword in file_path.lower() for keyword in ['doc', 'readme', 'md']):
                    changes["categories"].add("docs")
                elif any(keyword in file_path.lower() for keyword in ['config', 'setting']):
                    changes["categories"].add("config")
                else:
                    changes["categories"].add("code")
                
                # 変更タイプ
                if status.startswith('A'):
                    changes["added"].append(file_path)
                elif status.startswith('M'):
                    changes["modified"].append(file_path)
                elif status.startswith('D'):
                    changes["deleted"].append(file_path)
        
        return changes
    
    def _create_commit_message(self, changes: Dict[str, Any]) -> str:
        """変更内容からコミットメッセージを作成"""
        # 主要な変更タイプを判定
        total_changes = len(changes["added"]) + len(changes["modified"]) + len(changes["deleted"])
        
        if total_changes == 0:
            return "chore: minor updates"
        
        # カテゴリ別メッセージ
        if "test" in changes["categories"]:
            if changes["added"]:
                return f"test: add tests for {len(changes['added'])} files"
            else:
                return "test: update test cases"
        
        if "docs" in changes["categories"] and len(changes["categories"]) == 1:
            return "docs: update documentation"
        
        if "config" in changes["categories"] and len(changes["categories"]) == 1:
            return "chore: update configuration"
        
        # 新機能追加
        if len(changes["added"]) > len(changes["modified"]) + len(changes["deleted"]):
            return f"feat: add new functionality ({len(changes['added'])} files)"
        
        # バグ修正
        if any(keyword in str(changes).lower() for keyword in ['fix', 'bug', 'error']):
            return "fix: resolve issues"
        
        # リファクタリング
        if len(changes["modified"]) > 0 and len(changes["added"]) == 0:
            return f"refactor: improve code structure ({len(changes['modified'])} files)"
        
        # デフォルト
        return f"update: modify {total_changes} files"
    
    async def pull_changes(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """変更をプル"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            if branch is None:
                branch = repo.active_branch.name
            
            # プル実行
            remote_obj = repo.remotes[remote]
            pull_info = remote_obj.pull(branch)
            
            logger.info(f"Pulled changes from {remote}/{branch}")
            
            # 操作履歴記録
            self._record_operation(GitOperationType.PULL, {
                "remote": remote,
                "branch": branch,
                "info": str(pull_info)
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error pulling changes: {e}")
            return False
    
    async def push_changes(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """変更をプッシュ"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            if branch is None:
                branch = repo.active_branch.name
            
            # プッシュ実行
            remote_obj = repo.remotes[remote]
            push_info = remote_obj.push(branch)
            
            logger.info(f"Pushed changes to {remote}/{branch}")
            
            # 操作履歴記録
            self._record_operation(GitOperationType.PUSH, {
                "remote": remote,
                "branch": branch,
                "info": str(push_info)
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error pushing changes: {e}")
            return False
    
    async def merge_branch(self, source_branch: str, target_branch: Optional[str] = None) -> bool:
        """ブランチをマージ"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            if target_branch is None:
                target_branch = repo.active_branch.name
            else:
                # ターゲットブランチに切り替え
                await self.switch_branch(target_branch)
            
            # マージ実行
            source = repo.heads[source_branch]
            merge_base = repo.merge_base(repo.active_branch, source)[0]
            
            if merge_base == source.commit:
                logger.info(f"Branch {source_branch} is already merged")
                return True
            
            # マージ実行
            repo.git.merge(source_branch)
            
            logger.info(f"Merged {source_branch} into {target_branch}")
            
            # 操作履歴記録
            self._record_operation(GitOperationType.MERGE, {
                "source_branch": source_branch,
                "target_branch": target_branch
            })
            
            return True
            
        except git.GitCommandError as e:
            if "conflict" in str(e).lower():
                logger.warning(f"Merge conflict detected: {e}")
                if self.auto_conflict_resolution:
                    return await self._resolve_conflicts()
            else:
                logger.error(f"Error merging branch: {e}")
            return False
        except Exception as e:
            logger.error(f"Error merging branch: {e}")
            return False
    
    async def _resolve_conflicts(self) -> bool:
        """競合を自動解決"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            # 競合ファイルを取得
            conflicted_files = [item.a_path for item in repo.index.diff(None) 
                              if item.change_type == 'U']
            
            if not conflicted_files:
                return True
            
            logger.info(f"Resolving conflicts in {len(conflicted_files)} files")
            
            for file_path in conflicted_files:
                success = await self._resolve_file_conflict(file_path)
                if not success:
                    logger.warning(f"Could not auto-resolve conflict in {file_path}")
                    return False
            
            # 競合解決後にコミット
            repo.git.add(A=True)
            repo.index.commit("resolve merge conflicts")
            
            logger.info("All conflicts resolved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving conflicts: {e}")
            return False
    
    async def _resolve_file_conflict(self, file_path: str) -> bool:
        """ファイルの競合を解決"""
        try:
            full_path = self.current_repo_path / file_path
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 競合マーカーを検索
            conflict_pattern = r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> .*?\n'
            conflicts = re.findall(conflict_pattern, content, re.DOTALL)
            
            if not conflicts:
                return True
            
            # 簡単な競合解決ルール
            resolved_content = content
            for head_content, merge_content in conflicts:
                # 両方の変更を保持（簡単な例）
                if head_content.strip() and merge_content.strip():
                    resolved = f"{head_content.strip()}\n{merge_content.strip()}"
                elif head_content.strip():
                    resolved = head_content.strip()
                else:
                    resolved = merge_content.strip()
                
                # 競合マーカーを置換
                conflict_block = f"<<<<<<< HEAD\n{head_content}\n=======\n{merge_content}\n>>>>>>> "
                resolved_content = resolved_content.replace(conflict_block, resolved)
            
            # ファイルを保存
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(resolved_content)
            
            return True
            
        except Exception as e:
            logger.error(f"Error resolving file conflict {file_path}: {e}")
            return False
    
    def get_commit_history(self, max_count: int = 50) -> List[GitCommit]:
        """コミット履歴を取得"""
        repo = self.get_current_repo()
        if not repo:
            return []
        
        commits = []
        
        try:
            for commit in repo.iter_commits(max_count=max_count):
                # 変更ファイル数
                files_changed = list(commit.stats.files.keys())
                
                commits.append(GitCommit(
                    hash=commit.hexsha,
                    message=commit.message.strip(),
                    author=f"{commit.author.name} <{commit.author.email}>",
                    date=datetime.fromtimestamp(commit.committed_date).isoformat(),
                    files_changed=files_changed,
                    insertions=commit.stats.total['insertions'],
                    deletions=commit.stats.total['deletions']
                ))
            
            return commits
            
        except Exception as e:
            logger.error(f"Error getting commit history: {e}")
            return []
    
    def get_remotes(self) -> List[GitRemote]:
        """リモート一覧を取得"""
        repo = self.get_current_repo()
        if not repo:
            return []
        
        remotes = []
        
        try:
            for remote in repo.remotes:
                remotes.append(GitRemote(
                    name=remote.name,
                    url=list(remote.urls)[0] if remote.urls else "",
                    fetch_url=remote.url,
                    push_url=remote.pushurl or remote.url
                ))
            
            return remotes
            
        except Exception as e:
            logger.error(f"Error getting remotes: {e}")
            return []
    
    async def add_remote(self, name: str, url: str) -> bool:
        """リモートを追加"""
        repo = self.get_current_repo()
        if not repo:
            return False
        
        try:
            repo.create_remote(name, url)
            
            logger.info(f"Added remote: {name} -> {url}")
            
            # 操作履歴記録
            self._record_operation(GitOperationType.REMOTE, {
                "action": "add",
                "name": name,
                "url": url
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding remote: {e}")
            return False
    
    def _record_operation(self, operation_type: GitOperationType, details: Dict[str, Any]):
        """操作履歴を記録"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "type": operation_type.value,
            "details": details,
            "repo_path": str(self.current_repo_path) if self.current_repo_path else None
        }
        
        self.operation_history.append(record)
        
        # 最新1000件のみ保持
        if len(self.operation_history) > 1000:
            self.operation_history = self.operation_history[-1000:]
    
    def get_operation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """操作履歴を取得"""
        return self.operation_history[-limit:]
    
    def get_git_info(self) -> Dict[str, Any]:
        """Git情報を取得"""
        repo = self.get_current_repo()
        
        info = {
            "current_repo": str(self.current_repo_path) if self.current_repo_path else None,
            "total_repos": len(self.repos),
            "config": self.config,
            "ai_features": {
                "commit_messages": self.ai_commit_messages,
                "code_review": self.ai_code_review,
                "conflict_resolution": self.auto_conflict_resolution
            }
        }
        
        if repo:
            status = self.get_status()
            if status:
                info["status"] = asdict(status)
            
            info["remotes"] = [asdict(remote) for remote in self.get_remotes()]
            info["branches"] = [asdict(branch) for branch in self.get_branches()]
        
        return info


# グローバルGit管理インスタンス
_git_manager = None

def get_git_manager() -> GitManager:
    """Git管理のシングルトンインスタンス取得"""
    global _git_manager
    if _git_manager is None:
        _git_manager = GitManager()
    return _git_manager

def initialize_git_manager(workspace_root: str = "/tmp/autoai_workspace") -> GitManager:
    """Git管理を初期化"""
    global _git_manager
    _git_manager = GitManager(workspace_root)
    return _git_manager

