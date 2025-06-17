"""
Qwen3 4B Engine - AI推論エンジン

このモジュールは、Qwen3 4Bモデルを使用してAI推論を実行します。
タスク分解、コード生成、エラー解決などの機能を提供します。
"""

import os
import torch
import logging
from typing import Dict, List, Optional, Any
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    GenerationConfig,
    BitsAndBytesConfig
)
from dataclasses import dataclass
import json
import time

# Webブラウジング機能をインポート
from ..services.web_browser_tool import WebBrowserTool

logger = logging.getLogger(__name__)

@dataclass
class GenerationParams:
    """推論パラメータの設定"""
    max_length: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    do_sample: bool = True
    num_return_sequences: int = 1
    pad_token_id: Optional[int] = None
    eos_token_id: Optional[int] = None

class QwenEngine:
    """
    Qwen3 4Bモデルを使用したAI推論エンジン
    
    主な機能:
    - テキスト生成
    - コード生成
    - タスク分解
    - エラー分析
    - Webブラウジング（新機能）
    """
    
    def __init__(
        self, 
        model_path: str = "Qwen/Qwen2.5-Coder-4B-Instruct",
        cache_dir: str = "/app/models/cache",
        use_gpu: bool = True,
        use_quantization: bool = True
    ):
        """
        Qwenエンジンを初期化
        
        Args:
            model_path: Hugging Faceモデルパス
            cache_dir: モデルキャッシュディレクトリ
            use_gpu: GPU使用フラグ
            use_quantization: 量子化使用フラグ
        """
        self.model_path = model_path
        self.cache_dir = cache_dir
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.use_quantization = use_quantization
        
        # デバイス設定
        self.device = torch.device("cuda" if self.use_gpu else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # モデルとトークナイザーの初期化
        self.tokenizer = None
        self.model = None
        self.generation_config = None
        
        # Webブラウジングツールの初期化
        self.web_browser = WebBrowserTool()
        
        # 初期化
        self._initialize_model()
        
    def _initialize_model(self):
        """モデルとトークナイザーを初期化"""
        try:
            logger.info(f"Loading model: {self.model_path}")
            
            # トークナイザーの読み込み
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                cache_dir=self.cache_dir,
                trust_remote_code=True
            )
            
            # パディングトークンの設定
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # 量子化設定
            quantization_config = None
            if self.use_quantization and self.use_gpu:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
            
            # モデルの読み込み
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                cache_dir=self.cache_dir,
                torch_dtype=torch.float16 if self.use_gpu else torch.float32,
                device_map="auto" if self.use_gpu else None,
                quantization_config=quantization_config,
                trust_remote_code=True
            )
            
            # 生成設定
            self.generation_config = GenerationConfig(
                max_length=2048,
                temperature=0.7,
                top_p=0.9,
                top_k=50,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def generate_text(
        self, 
        prompt: str, 
        params: Optional[GenerationParams] = None,
        system_prompt: Optional[str] = None,
        use_web_search: bool = False
    ) -> str:
        """
        テキストを生成
        
        Args:
            prompt: 入力プロンプト
            params: 生成パラメータ
            system_prompt: システムプロンプト
            use_web_search: Web検索を使用するかどうか
            
        Returns:
            生成されたテキスト
        """
        if params is None:
            params = GenerationParams()
        
        # Web検索が必要かどうかを判断
        if use_web_search or self._should_use_web_search(prompt):
            web_context = self._get_web_context(prompt)
            if web_context:
                prompt = f"{prompt}\n\n参考情報:\n{web_context}"
            
        try:
            # プロンプトの構築
            full_prompt = self._build_prompt(prompt, system_prompt)
            
            # トークン化
            inputs = self.tokenizer(
                full_prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=1024
            )
            
            if self.use_gpu:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 生成
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=params.max_length,
                    temperature=params.temperature,
                    top_p=params.top_p,
                    top_k=params.top_k,
                    do_sample=params.do_sample,
                    num_return_sequences=params.num_return_sequences,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # デコード
            generated_text = self.tokenizer.decode(
                outputs[0], 
                skip_special_tokens=True
            )
            
            # 入力プロンプトを除去
            response = generated_text[len(full_prompt):].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise
    
    def _should_use_web_search(self, prompt: str) -> bool:
        """
        Web検索を使用すべきかどうかを判断
        
        Args:
            prompt: 入力プロンプト
            
        Returns:
            Web検索を使用すべきかどうか
        """
        search_keywords = [
            "最新", "新しい", "現在", "今", "2024", "2025",
            "ドキュメント", "公式", "チュートリアル", "ガイド",
            "エラー", "解決", "修正", "バグ",
            "ライブラリ", "フレームワーク", "API",
            "検索", "調べ", "探し", "見つけ"
        ]
        
        prompt_lower = prompt.lower()
        return any(keyword in prompt_lower for keyword in search_keywords)
    
    def _get_web_context(self, prompt: str) -> str:
        """
        プロンプトに基づいてWeb検索を実行し、コンテキストを取得
        
        Args:
            prompt: 入力プロンプト
            
        Returns:
            Web検索結果のコンテキスト
        """
        try:
            # 検索クエリを抽出
            search_query = self._extract_search_query(prompt)
            if not search_query:
                return ""
            
            logger.info(f"Web検索を実行: {search_query}")
            
            # Web検索とブラウジングを実行
            results = self.web_browser.search_and_browse(search_query, num_pages=2)
            
            if results.get('summary'):
                return results['summary']
            else:
                return ""
                
        except Exception as e:
            logger.error(f"Web検索エラー: {e}")
            return ""
    
    def _extract_search_query(self, prompt: str) -> str:
        """
        プロンプトから検索クエリを抽出
        
        Args:
            prompt: 入力プロンプト
            
        Returns:
            検索クエリ
        """
        # 簡単な実装：プロンプトから重要なキーワードを抽出
        import re
        
        # 技術的なキーワードを抽出
        tech_patterns = [
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b',  # CamelCase
            r'\b[a-z]+(?:-[a-z]+)+\b',           # kebab-case
            r'\b[a-z]+(?:_[a-z]+)+\b',           # snake_case
            r'\b\w+\.\w+\b',                     # package.module
        ]
        
        keywords = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, prompt)
            keywords.extend(matches)
        
        # 一般的なキーワードも追加
        common_keywords = ['Python', 'JavaScript', 'Docker', 'Flask', 'React', 'API', 'tutorial', 'error', 'fix']
        for keyword in common_keywords:
            if keyword.lower() in prompt.lower():
                keywords.append(keyword)
        
        # 重複を除去し、最初の3つを使用
        unique_keywords = list(dict.fromkeys(keywords))[:3]
        
        return ' '.join(unique_keywords) if unique_keywords else prompt[:50]
    
    def search_web(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Web検索を実行（直接呼び出し用）
        
        Args:
            query: 検索クエリ
            num_results: 取得する結果数
            
        Returns:
            検索結果
        """
        try:
            return self.web_browser.search(query, num_results)
        except Exception as e:
            logger.error(f"Web検索エラー: {e}")
            return {'query': query, 'results': [], 'total_results': 0, 'error': str(e)}
    
    def browse_page(self, url: str) -> Dict[str, Any]:
        """
        Webページをブラウジング（直接呼び出し用）
        
        Args:
            url: ブラウジングするURL
            
        Returns:
            ページ内容
        """
        try:
            return self.web_browser.browse_page(url)
        except Exception as e:
            logger.error(f"ページブラウジングエラー: {e}")
            return {'url': url, 'title': '', 'content': '', 'error': str(e)}
    
    def decompose_task(self, task_description: str) -> List[Dict[str, Any]]:
        """
        タスクを実行可能なステップに分解
        
        Args:
            task_description: タスクの説明
            
        Returns:
            ステップのリスト
        """
        system_prompt = """あなたは優秀なプロジェクトマネージャーです。
与えられたタスクを実行可能な小さなステップに分解してください。
必要に応じてWeb検索やドキュメント参照も含めてください。
各ステップは以下のJSON形式で出力してください：

{
  "steps": [
    {
      "id": 1,
      "title": "ステップのタイトル",
      "description": "詳細な説明",
      "type": "code|research|planning|testing|documentation|web_search",
      "estimated_time": "推定時間（分）",
      "dependencies": [前提となるステップのID],
      "tools": ["必要なツール"],
      "web_search_query": "Web検索が必要な場合のクエリ"
    }
  ]
}"""
        
        prompt = f"""
タスク: {task_description}

上記のタスクを実行可能なステップに分解してください。
最新の情報が必要な場合は、Web検索ステップも含めてください。
"""
        
        try:
            response = self.generate_text(prompt, system_prompt=system_prompt, use_web_search=True)
            
            # JSONの抽出
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result.get('steps', [])
            else:
                logger.warning("Failed to parse JSON from task decomposition")
                return []
                
        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            return []
    
    def analyze_error(self, error_message: str, code: str, context: str = "") -> Dict[str, Any]:
        """
        エラーを分析して解決策を提案
        
        Args:
            error_message: エラーメッセージ
            code: エラーが発生したコード
            context: 追加のコンテキスト
            
        Returns:
            エラー分析結果と解決策
        """
        system_prompt = """あなたは優秀なソフトウェアエンジニアです。
エラーを分析して解決策を提案してください。
必要に応じて最新のドキュメントやStack Overflowなどを参照してください。
以下のJSON形式で回答してください：

{
  "error_type": "エラーの種類",
  "root_cause": "根本原因",
  "severity": "low|medium|high|critical",
  "solutions": [
    {
      "description": "解決策の説明",
      "code_fix": "修正されたコード",
      "confidence": "信頼度（0-1）"
    }
  ],
  "prevention": "今後の予防策",
  "web_resources": ["参考になるWebリソース"]
}"""
        
        prompt = f"""
エラーメッセージ:
{error_message}

問題のあるコード:
```
{code}
```

コンテキスト:
{context}

このエラーを分析して解決策を提案してください。
最新の情報が必要な場合は、Web検索も活用してください。
"""
        
        try:
            response = self.generate_text(prompt, system_prompt=system_prompt, use_web_search=True)
            
            # JSONの抽出
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                logger.warning("Failed to parse JSON from error analysis")
                return {}
                
        except Exception as e:
            logger.error(f"Error analysis failed: {e}")
            return {}
    
    def generate_code(
        self, 
        requirements: str, 
        language: str = "python",
        style: str = "clean"
    ) -> str:
        """
        要件に基づいてコードを生成
        
        Args:
            requirements: 要件の説明
            language: プログラミング言語
            style: コーディングスタイル
            
        Returns:
            生成されたコード
        """
        system_prompt = f"""あなたは優秀な{language}プログラマーです。
{style}で読みやすく、保守性の高いコードを書いてください。
コメントも適切に含めてください。
最新のベストプラクティスに従ってください。"""
        
        prompt = f"""
以下の要件に基づいて{language}コードを生成してください：

要件:
{requirements}

コードのみを出力してください（説明は不要）。
"""
        
        try:
            response = self.generate_text(prompt, system_prompt=system_prompt, use_web_search=True)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return ""
    
    def _build_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        プロンプトを構築
        
        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト
            
        Returns:
            構築されたプロンプト
        """
        if system_prompt:
            return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        else:
            return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得
        
        Returns:
            モデル情報
        """
        return {
            "model_path": self.model_path,
            "device": str(self.device),
            "use_gpu": self.use_gpu,
            "use_quantization": self.use_quantization,
            "vocab_size": self.tokenizer.vocab_size if self.tokenizer else None,
            "model_size": sum(p.numel() for p in self.model.parameters()) if self.model else None,
            "web_browsing_enabled": True
        }
    
    def health_check(self) -> bool:
        """
        ヘルスチェック
        
        Returns:
            モデルが正常に動作しているかどうか
        """
        try:
            test_response = self.generate_text("Hello", GenerationParams(max_length=50))
            return len(test_response) > 0
        except Exception:
            return False

