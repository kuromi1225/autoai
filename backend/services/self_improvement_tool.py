"""
Self Improvement Tool - ツールセットの自己修正機能

このモジュールは、エージェントが自身のツールセットを分析し、
問題を特定して自動的に修正する機能を提供します。
"""

import os
import ast
import sys
import traceback
import subprocess
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class IssueType(Enum):
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    RUNTIME_ERROR = "runtime_error"
    LOGIC_ERROR = "logic_error"
    PERFORMANCE_ISSUE = "performance_issue"
    SECURITY_ISSUE = "security_issue"

class FixStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_MANUAL_INTERVENTION = "requires_manual_intervention"

@dataclass
class CodeIssue:
    """コードの問題を表すデータクラス"""
    issue_id: str
    file_path: str
    line_number: int
    issue_type: IssueType
    description: str
    severity: str  # low, medium, high, critical
    suggested_fix: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class FixAttempt:
    """修正試行を表すデータクラス"""
    attempt_id: str
    issue_id: str
    fix_description: str
    original_code: str
    modified_code: str
    status: FixStatus
    test_results: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class SelfImprovementTool:
    """ツールセットの自己修正機能を提供するクラス"""
    
    def __init__(self, tools_directory: str = "backend/services"):
        self.tools_directory = tools_directory
        self.issues: List[CodeIssue] = []
        self.fix_attempts: List[FixAttempt] = []
        self.backup_directory = os.path.join(tools_directory, ".backups")
        self.ensure_backup_directory()
        
    def ensure_backup_directory(self):
        """バックアップディレクトリの存在を確認し、必要に応じて作成"""
        if not os.path.exists(self.backup_directory):
            os.makedirs(self.backup_directory)
    
    def analyze_tools(self) -> List[CodeIssue]:
        """
        ツールセット内のすべてのPythonファイルを分析し、問題を特定
        
        Returns:
            List[CodeIssue]: 発見された問題のリスト
        """
        logger.info(f"Analyzing tools in directory: {self.tools_directory}")
        issues = []
        
        for root, dirs, files in os.walk(self.tools_directory):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    file_issues = self._analyze_file(file_path)
                    issues.extend(file_issues)
        
        self.issues.extend(issues)
        logger.info(f"Found {len(issues)} issues across {len(files)} files")
        return issues
    
    def _analyze_file(self, file_path: str) -> List[CodeIssue]:
        """
        単一のPythonファイルを分析
        
        Args:
            file_path: 分析するファイルのパス
            
        Returns:
            List[CodeIssue]: ファイル内で発見された問題のリスト
        """
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 構文エラーチェック
            syntax_issues = self._check_syntax(file_path, content)
            issues.extend(syntax_issues)
            
            # インポートエラーチェック
            import_issues = self._check_imports(file_path, content)
            issues.extend(import_issues)
            
            # セキュリティ問題チェック
            security_issues = self._check_security(file_path, content)
            issues.extend(security_issues)
            
            # パフォーマンス問題チェック
            performance_issues = self._check_performance(file_path, content)
            issues.extend(performance_issues)
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            issues.append(CodeIssue(
                issue_id=f"analysis_error_{datetime.utcnow().timestamp()}",
                file_path=file_path,
                line_number=0,
                issue_type=IssueType.RUNTIME_ERROR,
                description=f"Failed to analyze file: {str(e)}",
                severity="medium"
            ))
        
        return issues
    
    def _check_syntax(self, file_path: str, content: str) -> List[CodeIssue]:
        """構文エラーをチェック"""
        issues = []
        
        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append(CodeIssue(
                issue_id=f"syntax_{datetime.utcnow().timestamp()}",
                file_path=file_path,
                line_number=e.lineno or 0,
                issue_type=IssueType.SYNTAX_ERROR,
                description=f"Syntax error: {e.msg}",
                severity="high",
                context={"error_text": e.text}
            ))
        
        return issues
    
    def _check_imports(self, file_path: str, content: str) -> List[CodeIssue]:
        """インポートエラーをチェック"""
        issues = []
        
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    # インポートの検証を試行
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            try:
                                __import__(alias.name)
                            except ImportError:
                                issues.append(CodeIssue(
                                    issue_id=f"import_{datetime.utcnow().timestamp()}",
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    issue_type=IssueType.IMPORT_ERROR,
                                    description=f"Cannot import module: {alias.name}",
                                    severity="medium",
                                    suggested_fix=f"Install missing package or check module name: {alias.name}"
                                ))
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        try:
                            __import__(node.module)
                        except ImportError:
                            issues.append(CodeIssue(
                                issue_id=f"import_{datetime.utcnow().timestamp()}",
                                file_path=file_path,
                                line_number=node.lineno,
                                issue_type=IssueType.IMPORT_ERROR,
                                description=f"Cannot import module: {node.module}",
                                severity="medium",
                                suggested_fix=f"Install missing package or check module name: {node.module}"
                            ))
        except Exception as e:
            logger.warning(f"Could not check imports for {file_path}: {e}")
        
        return issues
    
    def _check_security(self, file_path: str, content: str) -> List[CodeIssue]:
        """セキュリティ問題をチェック"""
        issues = []
        
        # 危険な関数の使用をチェック
        dangerous_patterns = [
            ("eval(", "Use of eval() can be dangerous"),
            ("exec(", "Use of exec() can be dangerous"),
            ("os.system(", "Use of os.system() can be dangerous, consider subprocess"),
            ("shell=True", "shell=True in subprocess can be dangerous"),
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, message in dangerous_patterns:
                if pattern in line:
                    issues.append(CodeIssue(
                        issue_id=f"security_{datetime.utcnow().timestamp()}",
                        file_path=file_path,
                        line_number=line_num,
                        issue_type=IssueType.SECURITY_ISSUE,
                        description=message,
                        severity="high",
                        context={"line_content": line.strip()}
                    ))
        
        return issues
    
    def _check_performance(self, file_path: str, content: str) -> List[CodeIssue]:
        """パフォーマンス問題をチェック"""
        issues = []
        
        # 基本的なパフォーマンス問題をチェック
        performance_patterns = [
            ("for.*in.*range(len(", "Consider using enumerate() instead of range(len())"),
            (".*\+= .*str", "String concatenation in loop can be slow, consider using join()"),
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, message in performance_patterns:
                import re
                if re.search(pattern, line):
                    issues.append(CodeIssue(
                        issue_id=f"performance_{datetime.utcnow().timestamp()}",
                        file_path=file_path,
                        line_number=line_num,
                        issue_type=IssueType.PERFORMANCE_ISSUE,
                        description=message,
                        severity="low",
                        context={"line_content": line.strip()}
                    ))
        
        return issues
    
    def auto_fix_issue(self, issue: CodeIssue) -> FixAttempt:
        """
        問題を自動的に修正を試行
        
        Args:
            issue: 修正する問題
            
        Returns:
            FixAttempt: 修正試行の結果
        """
        logger.info(f"Attempting to auto-fix issue: {issue.issue_id}")
        
        # バックアップを作成
        backup_path = self._create_backup(issue.file_path)
        
        try:
            with open(issue.file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # 問題の種類に応じて修正を試行
            if issue.issue_type == IssueType.SYNTAX_ERROR:
                modified_content = self._fix_syntax_error(original_content, issue)
            elif issue.issue_type == IssueType.IMPORT_ERROR:
                modified_content = self._fix_import_error(original_content, issue)
            elif issue.issue_type == IssueType.SECURITY_ISSUE:
                modified_content = self._fix_security_issue(original_content, issue)
            elif issue.issue_type == IssueType.PERFORMANCE_ISSUE:
                modified_content = self._fix_performance_issue(original_content, issue)
            else:
                raise ValueError(f"Unsupported issue type: {issue.issue_type}")
            
            # 修正されたコードをテスト
            test_results = self._test_modified_code(issue.file_path, modified_content)
            
            if test_results.get('success', False):
                # テストが成功した場合、ファイルを更新
                with open(issue.file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                fix_attempt = FixAttempt(
                    attempt_id=f"fix_{datetime.utcnow().timestamp()}",
                    issue_id=issue.issue_id,
                    fix_description=f"Auto-fixed {issue.issue_type.value}",
                    original_code=original_content,
                    modified_code=modified_content,
                    status=FixStatus.COMPLETED,
                    test_results=test_results
                )
                
                logger.info(f"Successfully fixed issue: {issue.issue_id}")
            else:
                # テストが失敗した場合、バックアップから復元
                self._restore_from_backup(issue.file_path, backup_path)
                
                fix_attempt = FixAttempt(
                    attempt_id=f"fix_{datetime.utcnow().timestamp()}",
                    issue_id=issue.issue_id,
                    fix_description=f"Failed to auto-fix {issue.issue_type.value}",
                    original_code=original_content,
                    modified_code=modified_content,
                    status=FixStatus.FAILED,
                    test_results=test_results
                )
                
                logger.warning(f"Failed to fix issue: {issue.issue_id}")
        
        except Exception as e:
            # エラーが発生した場合、バックアップから復元
            self._restore_from_backup(issue.file_path, backup_path)
            
            fix_attempt = FixAttempt(
                attempt_id=f"fix_{datetime.utcnow().timestamp()}",
                issue_id=issue.issue_id,
                fix_description=f"Error during auto-fix: {str(e)}",
                original_code="",
                modified_code="",
                status=FixStatus.FAILED,
                test_results={"error": str(e)}
            )
            
            logger.error(f"Error fixing issue {issue.issue_id}: {e}")
        
        self.fix_attempts.append(fix_attempt)
        return fix_attempt
    
    def _create_backup(self, file_path: str) -> str:
        """ファイルのバックアップを作成"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{os.path.basename(file_path)}.{timestamp}.backup"
        backup_path = os.path.join(self.backup_directory, backup_filename)
        
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def _restore_from_backup(self, file_path: str, backup_path: str):
        """バックアップからファイルを復元"""
        shutil.copy2(backup_path, file_path)
        logger.info(f"Restored from backup: {backup_path}")
    
    def _fix_syntax_error(self, content: str, issue: CodeIssue) -> str:
        """構文エラーの修正を試行"""
        lines = content.split('\n')
        
        # 基本的な構文エラーの修正パターン
        if issue.line_number > 0 and issue.line_number <= len(lines):
            line = lines[issue.line_number - 1]
            
            # 一般的な構文エラーの修正
            if "invalid syntax" in issue.description.lower():
                # 括弧の不一致をチェック
                if line.count('(') != line.count(')'):
                    if line.count('(') > line.count(')'):
                        lines[issue.line_number - 1] = line + ')'
                elif line.count('[') != line.count(']'):
                    if line.count('[') > line.count(']'):
                        lines[issue.line_number - 1] = line + ']'
                elif line.count('{') != line.count('}'):
                    if line.count('{') > line.count('}'):
                        lines[issue.line_number - 1] = line + '}'
        
        return '\n'.join(lines)
    
    def _fix_import_error(self, content: str, issue: CodeIssue) -> str:
        """インポートエラーの修正を試行"""
        lines = content.split('\n')
        
        if issue.line_number > 0 and issue.line_number <= len(lines):
            line = lines[issue.line_number - 1]
            
            # 相対インポートの修正
            if "import" in line and not line.strip().startswith('#'):
                # 絶対インポートに変更を試行
                if line.strip().startswith('from .'):
                    lines[issue.line_number - 1] = line.replace('from .', 'from ')
                elif line.strip().startswith('import .'):
                    lines[issue.line_number - 1] = line.replace('import .', 'import ')
        
        return '\n'.join(lines)
    
    def _fix_security_issue(self, content: str, issue: CodeIssue) -> str:
        """セキュリティ問題の修正を試行"""
        lines = content.split('\n')
        
        if issue.line_number > 0 and issue.line_number <= len(lines):
            line = lines[issue.line_number - 1]
            
            # 危険な関数の置換
            if "eval(" in line:
                # evalの使用にコメントを追加
                lines[issue.line_number - 1] = f"# WARNING: eval() usage detected - {line}"
            elif "exec(" in line:
                # execの使用にコメントを追加
                lines[issue.line_number - 1] = f"# WARNING: exec() usage detected - {line}"
            elif "os.system(" in line:
                # os.systemをsubprocessに置換
                lines[issue.line_number - 1] = line.replace("os.system(", "subprocess.run(")
                # 必要に応じてimportを追加
                if "import subprocess" not in content:
                    lines.insert(0, "import subprocess")
        
        return '\n'.join(lines)
    
    def _fix_performance_issue(self, content: str, issue: CodeIssue) -> str:
        """パフォーマンス問題の修正を試行"""
        lines = content.split('\n')
        
        if issue.line_number > 0 and issue.line_number <= len(lines):
            line = lines[issue.line_number - 1]
            
            # range(len())をenumerate()に置換
            import re
            if re.search(r'for\s+\w+\s+in\s+range\(len\(', line):
                # 基本的な置換パターン
                match = re.search(r'for\s+(\w+)\s+in\s+range\(len\((\w+)\)\)', line)
                if match:
                    var_name = match.group(1)
                    list_name = match.group(2)
                    new_line = line.replace(
                        f"for {var_name} in range(len({list_name}))",
                        f"for {var_name}, item in enumerate({list_name})"
                    )
                    lines[issue.line_number - 1] = new_line
        
        return '\n'.join(lines)
    
    def _test_modified_code(self, file_path: str, modified_content: str) -> Dict[str, Any]:
        """修正されたコードをテスト"""
        test_results = {
            'success': False,
            'syntax_valid': False,
            'import_valid': False,
            'errors': []
        }
        
        try:
            # 構文チェック
            ast.parse(modified_content)
            test_results['syntax_valid'] = True
            
            # 一時ファイルでインポートテスト
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(modified_content)
                temp_file_path = temp_file.name
            
            try:
                # Pythonでファイルをチェック
                result = subprocess.run(
                    [sys.executable, '-m', 'py_compile', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    test_results['import_valid'] = True
                    test_results['success'] = True
                else:
                    test_results['errors'].append(result.stderr)
                    
            finally:
                os.unlink(temp_file_path)
                
        except SyntaxError as e:
            test_results['errors'].append(f"Syntax error: {e}")
        except Exception as e:
            test_results['errors'].append(f"Test error: {e}")
        
        return test_results
    
    def get_improvement_report(self) -> Dict[str, Any]:
        """自己改善の報告書を生成"""
        total_issues = len(self.issues)
        total_attempts = len(self.fix_attempts)
        successful_fixes = len([attempt for attempt in self.fix_attempts 
                              if attempt.status == FixStatus.COMPLETED])
        
        issue_types = {}
        for issue in self.issues:
            issue_type = issue.issue_type.value
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        severity_distribution = {}
        for issue in self.issues:
            severity = issue.severity
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        return {
            'summary': {
                'total_issues_found': total_issues,
                'total_fix_attempts': total_attempts,
                'successful_fixes': successful_fixes,
                'success_rate': successful_fixes / total_attempts if total_attempts > 0 else 0
            },
            'issue_breakdown': {
                'by_type': issue_types,
                'by_severity': severity_distribution
            },
            'recent_fixes': [
                {
                    'attempt_id': attempt.attempt_id,
                    'issue_id': attempt.issue_id,
                    'status': attempt.status.value,
                    'timestamp': attempt.timestamp.isoformat()
                }
                for attempt in sorted(self.fix_attempts, key=lambda x: x.timestamp, reverse=True)[:10]
            ],
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """改善のための推奨事項を生成"""
        recommendations = []
        
        # 高頻度の問題タイプに基づく推奨事項
        issue_types = {}
        for issue in self.issues:
            issue_type = issue.issue_type.value
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        if issue_types.get('import_error', 0) > 3:
            recommendations.append("Consider using virtual environments and requirements.txt for dependency management")
        
        if issue_types.get('security_issue', 0) > 0:
            recommendations.append("Review security practices and consider using static analysis tools")
        
        if issue_types.get('performance_issue', 0) > 2:
            recommendations.append("Consider code profiling and performance optimization")
        
        # 修正成功率に基づく推奨事項
        total_attempts = len(self.fix_attempts)
        successful_fixes = len([attempt for attempt in self.fix_attempts 
                              if attempt.status == FixStatus.COMPLETED])
        
        if total_attempts > 0:
            success_rate = successful_fixes / total_attempts
            if success_rate < 0.5:
                recommendations.append("Consider implementing more comprehensive testing before applying fixes")
        
        return recommendations

