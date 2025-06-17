"""
Advanced Error Resolver - 高度なエラー解決システム

このモジュールは、様々なタイプのエラーを自動的に分析し、
解決策を提案・実行する高度なエラー解決システムを提供します。
"""

import logging
import re
import traceback
import ast
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """エラータイプ"""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    RUNTIME_ERROR = "runtime_error"
    TYPE_ERROR = "type_error"
    ATTRIBUTE_ERROR = "attribute_error"
    NAME_ERROR = "name_error"
    INDEX_ERROR = "index_error"
    KEY_ERROR = "key_error"
    VALUE_ERROR = "value_error"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_ERROR = "permission_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_ERROR = "dependency_error"
    LOGIC_ERROR = "logic_error"
    PERFORMANCE_ERROR = "performance_error"

class Severity(Enum):
    """エラー重要度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ErrorContext:
    """エラーコンテキスト"""
    file_path: str
    line_number: int
    function_name: str
    code_snippet: str
    stack_trace: str
    environment: Dict[str, Any]

@dataclass
class Solution:
    """解決策"""
    description: str
    code_fix: Optional[str]
    commands: List[str]
    confidence: float  # 0.0 - 1.0
    estimated_time: int  # 分
    risk_level: Severity
    prerequisites: List[str]
    side_effects: List[str]

@dataclass
class ErrorAnalysis:
    """エラー分析結果"""
    error_type: ErrorType
    severity: Severity
    root_cause: str
    affected_components: List[str]
    solutions: List[Solution]
    prevention_tips: List[str]
    related_errors: List[str]

class AdvancedErrorResolver:
    """
    高度なエラー解決システム
    
    機能:
    - 多様なエラータイプの自動分類
    - 根本原因の分析
    - 複数の解決策の提案
    - 自動修正の実行
    - 予防策の提案
    """
    
    def __init__(self, qwen_engine, mcp_server):
        """
        エラー解決システムを初期化
        
        Args:
            qwen_engine: Qwenエンジンインスタンス
            mcp_server: MCPサーバーインスタンス
        """
        self.qwen_engine = qwen_engine
        self.mcp_server = mcp_server
        
        # エラーパターンの定義
        self.error_patterns = self._load_error_patterns()
        
        # 解決策データベース
        self.solution_database = self._load_solution_database()
        
        # 学習済みエラー
        self.learned_errors = {}
    
    async def analyze_and_resolve_error(
        self, 
        error_message: str,
        code: str = "",
        context: ErrorContext = None,
        auto_fix: bool = False
    ) -> ErrorAnalysis:
        """
        エラーを分析して解決策を提案
        
        Args:
            error_message: エラーメッセージ
            code: エラーが発生したコード
            context: エラーコンテキスト
            auto_fix: 自動修正フラグ
            
        Returns:
            エラー分析結果
        """
        try:
            logger.info(f"Analyzing error: {error_message[:100]}...")
            
            # エラータイプの分類
            error_type = self._classify_error(error_message, code)
            
            # 重要度の評価
            severity = self._assess_severity(error_message, error_type, context)
            
            # 根本原因の分析
            root_cause = await self._analyze_root_cause(
                error_message, code, context, error_type
            )
            
            # 影響範囲の分析
            affected_components = self._analyze_affected_components(
                error_message, code, context
            )
            
            # 解決策の生成
            solutions = await self._generate_solutions(
                error_message, code, context, error_type, root_cause
            )
            
            # 予防策の提案
            prevention_tips = self._suggest_prevention(error_type, root_cause)
            
            # 関連エラーの検索
            related_errors = self._find_related_errors(error_message, error_type)
            
            analysis = ErrorAnalysis(
                error_type=error_type,
                severity=severity,
                root_cause=root_cause,
                affected_components=affected_components,
                solutions=solutions,
                prevention_tips=prevention_tips,
                related_errors=related_errors
            )
            
            # 自動修正の実行
            if auto_fix and solutions:
                best_solution = max(solutions, key=lambda s: s.confidence)
                if best_solution.confidence > 0.8:
                    await self._apply_solution(best_solution, code, context)
            
            # 学習データに追加
            self._learn_from_error(error_message, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analysis failed: {e}")
            return ErrorAnalysis(
                error_type=ErrorType.RUNTIME_ERROR,
                severity=Severity.MEDIUM,
                root_cause="分析に失敗しました",
                affected_components=[],
                solutions=[],
                prevention_tips=[],
                related_errors=[]
            )
    
    def _classify_error(self, error_message: str, code: str) -> ErrorType:
        """エラータイプを分類"""
        
        error_message_lower = error_message.lower()
        
        # パターンマッチング
        for pattern, error_type in self.error_patterns.items():
            if re.search(pattern, error_message_lower):
                return ErrorType(error_type)
        
        # Pythonの標準例外
        if "syntaxerror" in error_message_lower:
            return ErrorType.SYNTAX_ERROR
        elif "importerror" in error_message_lower or "modulenotfounderror" in error_message_lower:
            return ErrorType.IMPORT_ERROR
        elif "typeerror" in error_message_lower:
            return ErrorType.TYPE_ERROR
        elif "attributeerror" in error_message_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif "nameerror" in error_message_lower:
            return ErrorType.NAME_ERROR
        elif "indexerror" in error_message_lower:
            return ErrorType.INDEX_ERROR
        elif "keyerror" in error_message_lower:
            return ErrorType.KEY_ERROR
        elif "valueerror" in error_message_lower:
            return ErrorType.VALUE_ERROR
        elif "filenotfounderror" in error_message_lower:
            return ErrorType.FILE_NOT_FOUND
        elif "permissionerror" in error_message_lower:
            return ErrorType.PERMISSION_ERROR
        
        # デフォルト
        return ErrorType.RUNTIME_ERROR
    
    def _assess_severity(
        self, 
        error_message: str, 
        error_type: ErrorType, 
        context: ErrorContext = None
    ) -> Severity:
        """エラーの重要度を評価"""
        
        # クリティカルなエラー
        critical_keywords = [
            "segmentation fault", "core dumped", "fatal", "critical",
            "system error", "out of memory", "stack overflow"
        ]
        
        if any(keyword in error_message.lower() for keyword in critical_keywords):
            return Severity.CRITICAL
        
        # 高重要度エラー
        if error_type in [ErrorType.SYNTAX_ERROR, ErrorType.IMPORT_ERROR]:
            return Severity.HIGH
        
        # データベース・ネットワークエラー
        if error_type in [ErrorType.DATABASE_ERROR, ErrorType.NETWORK_ERROR]:
            return Severity.HIGH
        
        # 中重要度エラー
        if error_type in [ErrorType.TYPE_ERROR, ErrorType.ATTRIBUTE_ERROR, ErrorType.NAME_ERROR]:
            return Severity.MEDIUM
        
        # 低重要度エラー
        return Severity.LOW
    
    async def _analyze_root_cause(
        self, 
        error_message: str, 
        code: str, 
        context: ErrorContext, 
        error_type: ErrorType
    ) -> str:
        """根本原因を分析"""
        
        analysis_prompt = f"""
以下のエラーの根本原因を分析してください：

エラーメッセージ: {error_message}
エラータイプ: {error_type.value}
コード:
```
{code}
```

コンテキスト:
- ファイル: {context.file_path if context else 'unknown'}
- 行番号: {context.line_number if context else 'unknown'}
- 関数: {context.function_name if context else 'unknown'}

根本原因を簡潔に説明してください（1-2文で）。
"""
        
        try:
            root_cause = self.qwen_engine.generate_text(analysis_prompt)
            return root_cause.strip()
        except Exception as e:
            logger.error(f"Root cause analysis failed: {e}")
            return "根本原因の分析に失敗しました"
    
    def _analyze_affected_components(
        self, 
        error_message: str, 
        code: str, 
        context: ErrorContext = None
    ) -> List[str]:
        """影響を受けるコンポーネントを分析"""
        
        components = []
        
        # ファイル名から推測
        if context and context.file_path:
            file_name = context.file_path.split('/')[-1]
            if file_name.endswith('.py'):
                components.append(f"Python module: {file_name}")
        
        # インポート文から推測
        import_matches = re.findall(r'import\s+(\w+)', code)
        for module in import_matches:
            components.append(f"Dependency: {module}")
        
        # 関数・クラス名から推測
        if context and context.function_name:
            components.append(f"Function: {context.function_name}")
        
        return components
    
    async def _generate_solutions(
        self, 
        error_message: str, 
        code: str, 
        context: ErrorContext, 
        error_type: ErrorType, 
        root_cause: str
    ) -> List[Solution]:
        """解決策を生成"""
        
        solutions = []
        
        # データベースから既知の解決策を検索
        db_solutions = self._search_solution_database(error_message, error_type)
        solutions.extend(db_solutions)
        
        # AIによる解決策生成
        ai_solutions = await self._generate_ai_solutions(
            error_message, code, context, error_type, root_cause
        )
        solutions.extend(ai_solutions)
        
        # 信頼度でソート
        solutions.sort(key=lambda s: s.confidence, reverse=True)
        
        return solutions[:5]  # 上位5つの解決策
    
    async def _generate_ai_solutions(
        self, 
        error_message: str, 
        code: str, 
        context: ErrorContext, 
        error_type: ErrorType, 
        root_cause: str
    ) -> List[Solution]:
        """AIによる解決策生成"""
        
        solution_prompt = f"""
以下のエラーの解決策を提案してください：

エラーメッセージ: {error_message}
エラータイプ: {error_type.value}
根本原因: {root_cause}

問題のあるコード:
```
{code}
```

以下のJSON形式で複数の解決策を提案してください：

{{
  "solutions": [
    {{
      "description": "解決策の説明",
      "code_fix": "修正されたコード（必要な場合）",
      "commands": ["実行すべきコマンド"],
      "confidence": "信頼度（0.0-1.0）",
      "estimated_time": "推定修正時間（分）",
      "risk_level": "low|medium|high|critical",
      "prerequisites": ["前提条件"],
      "side_effects": ["副作用"]
    }}
  ]
}}
"""
        
        try:
            response = self.qwen_engine.generate_text(solution_prompt)
            
            # JSONの抽出
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return []
            
            data = json.loads(json_match.group())
            solutions_data = data.get('solutions', [])
            
            solutions = []
            for sol_data in solutions_data:
                solution = Solution(
                    description=sol_data.get('description', ''),
                    code_fix=sol_data.get('code_fix'),
                    commands=sol_data.get('commands', []),
                    confidence=float(sol_data.get('confidence', 0.5)),
                    estimated_time=int(sol_data.get('estimated_time', 10)),
                    risk_level=Severity[sol_data.get('risk_level', 'medium').upper()],
                    prerequisites=sol_data.get('prerequisites', []),
                    side_effects=sol_data.get('side_effects', [])
                )
                solutions.append(solution)
            
            return solutions
            
        except Exception as e:
            logger.error(f"AI solution generation failed: {e}")
            return []
    
    def _search_solution_database(
        self, 
        error_message: str, 
        error_type: ErrorType
    ) -> List[Solution]:
        """解決策データベースから検索"""
        
        solutions = []
        
        # エラータイプ別の既知解決策
        if error_type in self.solution_database:
            type_solutions = self.solution_database[error_type]
            
            for pattern, solution_data in type_solutions.items():
                if re.search(pattern, error_message, re.IGNORECASE):
                    solution = Solution(
                        description=solution_data['description'],
                        code_fix=solution_data.get('code_fix'),
                        commands=solution_data.get('commands', []),
                        confidence=solution_data.get('confidence', 0.8),
                        estimated_time=solution_data.get('estimated_time', 5),
                        risk_level=Severity[solution_data.get('risk_level', 'low').upper()],
                        prerequisites=solution_data.get('prerequisites', []),
                        side_effects=solution_data.get('side_effects', [])
                    )
                    solutions.append(solution)
        
        return solutions
    
    async def _apply_solution(
        self, 
        solution: Solution, 
        original_code: str, 
        context: ErrorContext = None
    ) -> bool:
        """解決策を適用"""
        
        try:
            logger.info(f"Applying solution: {solution.description}")
            
            # コマンドの実行
            for command in solution.commands:
                result = await self.mcp_server.handle_request({
                    "id": "auto_fix",
                    "method": "tools/call",
                    "params": {
                        "name": "shell_exec",
                        "arguments": {"command": command}
                    }
                })
                
                if not result.get('result', {}).get('content', [{}])[0].get('text', '{}'):
                    logger.warning(f"Command failed: {command}")
            
            # コード修正の適用
            if solution.code_fix and context and context.file_path:
                await self.mcp_server.handle_request({
                    "id": "auto_fix",
                    "method": "tools/call",
                    "params": {
                        "name": "file_write",
                        "arguments": {
                            "path": context.file_path,
                            "content": solution.code_fix
                        }
                    }
                })
            
            logger.info("Solution applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply solution: {e}")
            return False
    
    def _suggest_prevention(self, error_type: ErrorType, root_cause: str) -> List[str]:
        """予防策を提案"""
        
        prevention_map = {
            ErrorType.SYNTAX_ERROR: [
                "コードエディタの構文チェック機能を有効にする",
                "リンターツール（flake8, pylint）を使用する",
                "IDEの自動補完機能を活用する"
            ],
            ErrorType.IMPORT_ERROR: [
                "requirements.txtで依存関係を明確に管理する",
                "仮想環境を使用して依存関係を分離する",
                "インポート前にモジュールの存在を確認する"
            ],
            ErrorType.TYPE_ERROR: [
                "型ヒント（Type Hints）を使用する",
                "mypyなどの静的型チェッカーを使用する",
                "入力値の型を事前に検証する"
            ],
            ErrorType.NAME_ERROR: [
                "変数名のスペルチェックを行う",
                "スコープを意識した変数定義を行う",
                "未定義変数の使用前チェックを実装する"
            ]
        }
        
        return prevention_map.get(error_type, [
            "コードレビューを実施する",
            "単体テストを充実させる",
            "ログ出力を適切に設定する"
        ])
    
    def _find_related_errors(self, error_message: str, error_type: ErrorType) -> List[str]:
        """関連エラーを検索"""
        
        related = []
        
        # 学習済みエラーから類似エラーを検索
        for learned_error, analysis in self.learned_errors.items():
            if analysis.error_type == error_type:
                # 簡単な類似度計算
                common_words = set(error_message.lower().split()) & set(learned_error.lower().split())
                if len(common_words) > 2:
                    related.append(learned_error)
        
        return related[:3]  # 上位3つ
    
    def _learn_from_error(self, error_message: str, analysis: ErrorAnalysis):
        """エラーから学習"""
        
        # 学習データに追加
        self.learned_errors[error_message] = analysis
        
        # 学習データのサイズ制限
        if len(self.learned_errors) > 1000:
            # 古いデータを削除
            oldest_key = next(iter(self.learned_errors))
            del self.learned_errors[oldest_key]
    
    def _load_error_patterns(self) -> Dict[str, str]:
        """エラーパターンを読み込み"""
        return {
            r"no module named": "import_error",
            r"cannot import": "import_error",
            r"syntax error": "syntax_error",
            r"invalid syntax": "syntax_error",
            r"indentation error": "syntax_error",
            r"unexpected token": "syntax_error",
            r"file not found": "file_not_found",
            r"permission denied": "permission_error",
            r"connection refused": "network_error",
            r"timeout": "network_error",
            r"database": "database_error",
            r"sql": "database_error",
            r"out of memory": "performance_error",
            r"stack overflow": "performance_error"
        }
    
    def _load_solution_database(self) -> Dict[ErrorType, Dict[str, Dict[str, Any]]]:
        """解決策データベースを読み込み"""
        return {
            ErrorType.IMPORT_ERROR: {
                r"no module named '(\w+)'": {
                    "description": "必要なモジュールをインストールする",
                    "commands": ["pip install {module}"],
                    "confidence": 0.9,
                    "estimated_time": 2,
                    "risk_level": "low"
                }
            },
            ErrorType.SYNTAX_ERROR: {
                r"invalid syntax": {
                    "description": "構文エラーを修正する",
                    "confidence": 0.7,
                    "estimated_time": 5,
                    "risk_level": "low"
                }
            },
            ErrorType.FILE_NOT_FOUND: {
                r"no such file or directory": {
                    "description": "ファイルパスを確認し、必要に応じてファイルを作成する",
                    "confidence": 0.8,
                    "estimated_time": 3,
                    "risk_level": "low"
                }
            }
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計を取得"""
        
        if not self.learned_errors:
            return {"total_errors": 0}
        
        error_types = [analysis.error_type for analysis in self.learned_errors.values()]
        severity_levels = [analysis.severity for analysis in self.learned_errors.values()]
        
        from collections import Counter
        
        return {
            "total_errors": len(self.learned_errors),
            "error_type_distribution": dict(Counter(error_types)),
            "severity_distribution": dict(Counter(severity_levels)),
            "most_common_error": Counter(error_types).most_common(1)[0] if error_types else None,
            "resolution_rate": sum(1 for analysis in self.learned_errors.values() 
                                 if analysis.solutions) / len(self.learned_errors)
        }

