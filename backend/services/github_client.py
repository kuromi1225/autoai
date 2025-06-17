"""
GitHub Client - 高度なGitHub統合クライアント

このモジュールは、GitHubとの統合機能を提供し、
自動コミット、ブランチ管理、プルリクエスト作成などを行います。
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import git
from github import Github, GithubException
from github.Repository import Repository
from github.PullRequest import PullRequest
from github.Issue import Issue
import tempfile
import shutil

logger = logging.getLogger(__name__)

@dataclass
class CommitInfo:
    """コミット情報"""
    sha: str
    message: str
    author: str
    date: datetime
    files_changed: List[str]
    additions: int
    deletions: int

@dataclass
class BranchInfo:
    """ブランチ情報"""
    name: str
    sha: str
    is_default: bool
    is_protected: bool
    ahead_by: int
    behind_by: int

@dataclass
class PullRequestInfo:
    """プルリクエスト情報"""
    number: int
    title: str
    body: str
    state: str
    head_branch: str
    base_branch: str
    author: str
    created_at: datetime
    mergeable: bool

class GitHubClient:
    """
    高度なGitHub統合クライアント
    
    機能:
    - リポジトリの自動管理
    - インテリジェントなコミット
    - ブランチ戦略の実装
    - 自動プルリクエスト作成
    - コードレビューの自動化
    """
    
    def __init__(
        self, 
        token: str, 
        workspace_dir: str = "/app/workspace",
        qwen_engine=None
    ):
        """
        GitHubクライアントを初期化
        
        Args:
            token: GitHub Personal Access Token
            workspace_dir: 作業ディレクトリ
            qwen_engine: Qwenエンジン（コミットメッセージ生成用）
        """
        self.token = token
        self.workspace_dir = workspace_dir
        self.qwen_engine = qwen_engine
        
        # GitHub API クライアント
        self.github = Github(token)
        
        # 現在のリポジトリ情報
        self.current_repo: Optional[Repository] = None
        self.current_repo_path: Optional[str] = None
        self.git_repo: Optional[git.Repo] = None
        
        # 設定
        self.default_branch = "main"
        self.feature_branch_prefix = "feature/"
        self.auto_pr_enabled = True
        
        logger.info("GitHub client initialized")
    
    def setup_repository(
        self, 
        repo_url: str, 
        local_path: str = None,
        clone_if_not_exists: bool = True
    ) -> bool:
        """
        リポジトリをセットアップ
        
        Args:
            repo_url: GitHubリポジトリURL
            local_path: ローカルパス
            clone_if_not_exists: 存在しない場合にクローンするか
            
        Returns:
            セットアップ成功フラグ
        """
        try:
            # リポジトリ名を抽出
            if repo_url.startswith("https://github.com/"):
                repo_name = repo_url.replace("https://github.com/", "").replace(".git", "")
            else:
                repo_name = repo_url
            
            # GitHub APIでリポジトリを取得
            self.current_repo = self.github.get_repo(repo_name)
            
            # ローカルパスの設定
            if not local_path:
                local_path = os.path.join(self.workspace_dir, repo_name.split('/')[-1])
            
            self.current_repo_path = local_path
            
            # ローカルリポジトリの設定
            if os.path.exists(local_path):
                self.git_repo = git.Repo(local_path)
                logger.info(f"Using existing repository: {local_path}")
            elif clone_if_not_exists:
                self.git_repo = git.Repo.clone_from(repo_url, local_path)
                logger.info(f"Cloned repository: {repo_url} -> {local_path}")
            else:
                logger.error(f"Repository not found: {local_path}")
                return False
            
            # デフォルトブランチを取得
            self.default_branch = self.current_repo.default_branch
            
            logger.info(f"Repository setup completed: {repo_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup repository: {e}")
            return False
    
    def create_repository(
        self, 
        name: str, 
        description: str = "",
        private: bool = False,
        auto_init: bool = True
    ) -> bool:
        """
        新しいリポジトリを作成
        
        Args:
            name: リポジトリ名
            description: 説明
            private: プライベートリポジトリフラグ
            auto_init: 自動初期化フラグ
            
        Returns:
            作成成功フラグ
        """
        try:
            user = self.github.get_user()
            
            repo = user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=auto_init
            )
            
            self.current_repo = repo
            
            # ローカルにクローン
            local_path = os.path.join(self.workspace_dir, name)
            self.git_repo = git.Repo.clone_from(repo.clone_url, local_path)
            self.current_repo_path = local_path
            
            logger.info(f"Repository created: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create repository: {e}")
            return False
    
    def intelligent_commit(
        self, 
        files: List[str] = None,
        message: str = None,
        auto_generate_message: bool = True,
        create_branch: bool = False,
        branch_name: str = None
    ) -> Optional[str]:
        """
        インテリジェントなコミット
        
        Args:
            files: コミットするファイルリスト
            message: コミットメッセージ
            auto_generate_message: 自動メッセージ生成フラグ
            create_branch: 新しいブランチを作成するか
            branch_name: ブランチ名
            
        Returns:
            コミットSHA
        """
        try:
            if not self.git_repo:
                logger.error("No git repository configured")
                return None
            
            # 新しいブランチの作成
            if create_branch:
                if not branch_name:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    branch_name = f"{self.feature_branch_prefix}auto_{timestamp}"
                
                self._create_and_checkout_branch(branch_name)
            
            # ファイルの追加
            if files:
                for file_path in files:
                    self.git_repo.index.add([file_path])
            else:
                # 全ての変更をステージング
                self.git_repo.git.add(A=True)
            
            # 変更がない場合は終了
            if not self.git_repo.index.diff("HEAD"):
                logger.info("No changes to commit")
                return None
            
            # コミットメッセージの生成
            if not message and auto_generate_message:
                message = self._generate_commit_message()
            
            if not message:
                message = "Auto-commit: Update files"
            
            # コミット実行
            commit = self.git_repo.index.commit(message)
            
            logger.info(f"Committed: {commit.hexsha[:8]} - {message}")
            return commit.hexsha
            
        except Exception as e:
            logger.error(f"Failed to commit: {e}")
            return None
    
    def push_changes(self, branch_name: str = None, force: bool = False) -> bool:
        """
        変更をプッシュ
        
        Args:
            branch_name: ブランチ名
            force: 強制プッシュフラグ
            
        Returns:
            プッシュ成功フラグ
        """
        try:
            if not self.git_repo:
                logger.error("No git repository configured")
                return False
            
            if not branch_name:
                branch_name = self.git_repo.active_branch.name
            
            origin = self.git_repo.remote("origin")
            
            if force:
                origin.push(branch_name, force=True)
            else:
                origin.push(branch_name)
            
            logger.info(f"Pushed changes to {branch_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to push changes: {e}")
            return False
    
    def create_pull_request(
        self, 
        title: str = None,
        body: str = None,
        head_branch: str = None,
        base_branch: str = None,
        auto_generate_content: bool = True
    ) -> Optional[PullRequestInfo]:
        """
        プルリクエストを作成
        
        Args:
            title: タイトル
            body: 本文
            head_branch: ソースブランチ
            base_branch: ターゲットブランチ
            auto_generate_content: 自動コンテンツ生成フラグ
            
        Returns:
            プルリクエスト情報
        """
        try:
            if not self.current_repo:
                logger.error("No repository configured")
                return None
            
            if not head_branch:
                head_branch = self.git_repo.active_branch.name
            
            if not base_branch:
                base_branch = self.default_branch
            
            # タイトルと本文の自動生成
            if auto_generate_content:
                if not title or not body:
                    generated_content = self._generate_pr_content(head_branch, base_branch)
                    if not title:
                        title = generated_content.get("title", f"Merge {head_branch} into {base_branch}")
                    if not body:
                        body = generated_content.get("body", "Auto-generated pull request")
            
            # プルリクエスト作成
            pr = self.current_repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            pr_info = PullRequestInfo(
                number=pr.number,
                title=pr.title,
                body=pr.body,
                state=pr.state,
                head_branch=pr.head.ref,
                base_branch=pr.base.ref,
                author=pr.user.login,
                created_at=pr.created_at,
                mergeable=pr.mergeable
            )
            
            logger.info(f"Pull request created: #{pr.number}")
            return pr_info
            
        except Exception as e:
            logger.error(f"Failed to create pull request: {e}")
            return None
    
    def auto_merge_pr(self, pr_number: int, merge_method: str = "squash") -> bool:
        """
        プルリクエストを自動マージ
        
        Args:
            pr_number: プルリクエスト番号
            merge_method: マージ方法 (merge, squash, rebase)
            
        Returns:
            マージ成功フラグ
        """
        try:
            if not self.current_repo:
                logger.error("No repository configured")
                return False
            
            pr = self.current_repo.get_pull(pr_number)
            
            # マージ可能性をチェック
            if not pr.mergeable:
                logger.error(f"Pull request #{pr_number} is not mergeable")
                return False
            
            # ステータスチェックの確認
            if not self._check_pr_status(pr):
                logger.error(f"Pull request #{pr_number} has failing status checks")
                return False
            
            # マージ実行
            merge_result = pr.merge(merge_method=merge_method)
            
            if merge_result.merged:
                logger.info(f"Pull request #{pr_number} merged successfully")
                return True
            else:
                logger.error(f"Failed to merge pull request #{pr_number}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to auto-merge PR: {e}")
            return False
    
    def get_repository_info(self) -> Dict[str, Any]:
        """リポジトリ情報を取得"""
        try:
            if not self.current_repo:
                return {}
            
            return {
                "name": self.current_repo.name,
                "full_name": self.current_repo.full_name,
                "description": self.current_repo.description,
                "url": self.current_repo.html_url,
                "default_branch": self.current_repo.default_branch,
                "private": self.current_repo.private,
                "stars": self.current_repo.stargazers_count,
                "forks": self.current_repo.forks_count,
                "issues": self.current_repo.open_issues_count,
                "language": self.current_repo.language,
                "size": self.current_repo.size,
                "created_at": self.current_repo.created_at.isoformat(),
                "updated_at": self.current_repo.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get repository info: {e}")
            return {}
    
    def get_commit_history(self, limit: int = 10) -> List[CommitInfo]:
        """コミット履歴を取得"""
        try:
            if not self.current_repo:
                return []
            
            commits = []
            for commit in self.current_repo.get_commits()[:limit]:
                commit_info = CommitInfo(
                    sha=commit.sha,
                    message=commit.commit.message,
                    author=commit.commit.author.name,
                    date=commit.commit.author.date,
                    files_changed=[f.filename for f in commit.files],
                    additions=commit.stats.additions,
                    deletions=commit.stats.deletions
                )
                commits.append(commit_info)
            
            return commits
            
        except Exception as e:
            logger.error(f"Failed to get commit history: {e}")
            return []
    
    def get_branch_info(self) -> List[BranchInfo]:
        """ブランチ情報を取得"""
        try:
            if not self.current_repo:
                return []
            
            branches = []
            for branch in self.current_repo.get_branches():
                # ブランチの比較情報を取得
                try:
                    comparison = self.current_repo.compare(
                        self.default_branch, 
                        branch.name
                    )
                    ahead_by = comparison.ahead_by
                    behind_by = comparison.behind_by
                except:
                    ahead_by = 0
                    behind_by = 0
                
                branch_info = BranchInfo(
                    name=branch.name,
                    sha=branch.commit.sha,
                    is_default=branch.name == self.default_branch,
                    is_protected=branch.protected,
                    ahead_by=ahead_by,
                    behind_by=behind_by
                )
                branches.append(branch_info)
            
            return branches
            
        except Exception as e:
            logger.error(f"Failed to get branch info: {e}")
            return []
    
    def _create_and_checkout_branch(self, branch_name: str) -> bool:
        """新しいブランチを作成してチェックアウト"""
        try:
            # ブランチが既に存在するかチェック
            if branch_name in [b.name for b in self.git_repo.branches]:
                self.git_repo.git.checkout(branch_name)
                logger.info(f"Checked out existing branch: {branch_name}")
            else:
                new_branch = self.git_repo.create_head(branch_name)
                new_branch.checkout()
                logger.info(f"Created and checked out new branch: {branch_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create/checkout branch: {e}")
            return False
    
    def _generate_commit_message(self) -> str:
        """コミットメッセージを自動生成"""
        try:
            if not self.qwen_engine:
                return "Auto-commit: Update files"
            
            # 変更されたファイルの情報を取得
            diff = self.git_repo.git.diff("--cached", "--name-status")
            
            if not diff:
                return "Auto-commit: No changes"
            
            # AIにコミットメッセージを生成させる
            prompt = f"""
以下のGit差分に基づいて、適切なコミットメッセージを生成してください：

変更されたファイル:
{diff}

コミットメッセージは以下の形式で生成してください：
- 50文字以内の簡潔なタイトル
- 必要に応じて詳細な説明
- 従来のコミットメッセージ規約に従う

コミットメッセージのみを出力してください。
"""
            
            message = self.qwen_engine.generate_text(prompt)
            return message.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate commit message: {e}")
            return "Auto-commit: Update files"
    
    def _generate_pr_content(self, head_branch: str, base_branch: str) -> Dict[str, str]:
        """プルリクエストのタイトルと本文を自動生成"""
        try:
            if not self.qwen_engine:
                return {
                    "title": f"Merge {head_branch} into {base_branch}",
                    "body": "Auto-generated pull request"
                }
            
            # ブランチ間の差分を取得
            comparison = self.current_repo.compare(base_branch, head_branch)
            
            commits = []
            for commit in comparison.commits:
                commits.append({
                    "message": commit.commit.message,
                    "author": commit.commit.author.name,
                    "files": [f.filename for f in commit.files]
                })
            
            # AIにPRコンテンツを生成させる
            prompt = f"""
以下の情報に基づいて、プルリクエストのタイトルと本文を生成してください：

ソースブランチ: {head_branch}
ターゲットブランチ: {base_branch}

コミット履歴:
{json.dumps(commits, ensure_ascii=False, indent=2)}

以下のJSON形式で出力してください：
{{
  "title": "簡潔で分かりやすいタイトル",
  "body": "変更内容の詳細説明"
}}
"""
            
            response = self.qwen_engine.generate_text(prompt)
            
            # JSONの抽出
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                import json
                content = json.loads(json_match.group())
                return content
            
            return {
                "title": f"Merge {head_branch} into {base_branch}",
                "body": response.strip()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate PR content: {e}")
            return {
                "title": f"Merge {head_branch} into {base_branch}",
                "body": "Auto-generated pull request"
            }
    
    def _check_pr_status(self, pr: PullRequest) -> bool:
        """プルリクエストのステータスチェックを確認"""
        try:
            # 最新のコミットのステータスを取得
            commit = pr.head.sha
            statuses = self.current_repo.get_commit(commit).get_statuses()
            
            # すべてのステータスが成功している必要がある
            for status in statuses:
                if status.state not in ["success", "pending"]:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check PR status: {e}")
            return False
    
    def cleanup_merged_branches(self, exclude_branches: List[str] = None) -> int:
        """マージ済みブランチをクリーンアップ"""
        try:
            if not self.git_repo:
                return 0
            
            if not exclude_branches:
                exclude_branches = [self.default_branch, "develop", "staging"]
            
            cleaned_count = 0
            
            # リモートブランチの情報を更新
            self.git_repo.remote("origin").fetch(prune=True)
            
            # ローカルブランチをチェック
            for branch in self.git_repo.branches:
                if branch.name in exclude_branches:
                    continue
                
                # マージ済みかチェック
                try:
                    merge_base = self.git_repo.merge_base(
                        branch.commit, 
                        self.git_repo.branches[self.default_branch].commit
                    )[0]
                    
                    if merge_base == branch.commit:
                        # マージ済みブランチを削除
                        self.git_repo.delete_head(branch, force=True)
                        cleaned_count += 1
                        logger.info(f"Deleted merged branch: {branch.name}")
                        
                except Exception as e:
                    logger.warning(f"Failed to check branch {branch.name}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup branches: {e}")
            return 0

