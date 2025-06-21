"""
QwQ-32B ローカル推論エンジン

Hugging Face TransformersベースのQwQ-32B推論システム
有料API不使用、完全ローカル実行
"""

import torch
import logging
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    BitsAndBytesConfig,
    pipeline
)
from typing import Dict, List, Optional, Any, Generator
import asyncio
import threading
import queue
import time
import psutil
import gc
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class QwQInferenceEngine:
    """QwQ-32B推論エンジン"""
    
    def __init__(self, 
                 model_name: str = "Qwen/QwQ-32B-Preview",
                 device: str = "auto",
                 quantization: bool = True,
                 max_memory: Optional[Dict] = None):
        """
        初期化
        
        Args:
            model_name: モデル名
            device: 実行デバイス (auto, cuda, cpu)
            quantization: 量子化使用フラグ
            max_memory: 最大メモリ使用量
        """
        self.model_name = model_name
        self.device = device
        self.quantization = quantization
        self.max_memory = max_memory
        
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self.is_loaded = False
        
        # パフォーマンス監視
        self.inference_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_time': 0.0,
            'average_tokens_per_second': 0.0,
            'memory_usage': 0.0
        }
        
        # 非同期処理用
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
    
    def load_model(self) -> bool:
        """モデルをロード"""
        try:
            logger.info(f"Loading QwQ-32B model: {self.model_name}")
            
            # デバイス設定
            if self.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            logger.info(f"Using device: {self.device}")
            
            # 量子化設定
            quantization_config = None
            if self.quantization and self.device == "cuda":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                logger.info("Using 4-bit quantization")
            
            # トークナイザーロード
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # モデルロード
            model_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                "device_map": "auto" if self.device == "cuda" else None,
            }
            
            if quantization_config:
                model_kwargs["quantization_config"] = quantization_config
            
            if self.max_memory:
                model_kwargs["max_memory"] = self.max_memory
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs
            )
            
            # パイプライン作成
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map="auto" if self.device == "cuda" else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            self.is_loaded = True
            logger.info("QwQ-32B model loaded successfully")
            
            # メモリ使用量記録
            self._update_memory_stats()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load QwQ-32B model: {e}")
            return False
    
    def unload_model(self):
        """モデルをアンロード"""
        try:
            if self.model:
                del self.model
            if self.tokenizer:
                del self.tokenizer
            if self.pipeline:
                del self.pipeline
            
            # GPU メモリクリア
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # ガベージコレクション
            gc.collect()
            
            self.is_loaded = False
            logger.info("QwQ-32B model unloaded")
            
        except Exception as e:
            logger.error(f"Error unloading model: {e}")
    
    def generate_response(self, 
                         prompt: str,
                         max_length: int = 2048,
                         temperature: float = 0.7,
                         top_p: float = 0.9,
                         top_k: int = 50,
                         do_sample: bool = True,
                         num_return_sequences: int = 1,
                         stream: bool = False) -> str:
        """
        テキスト生成
        
        Args:
            prompt: 入力プロンプト
            max_length: 最大生成長
            temperature: 温度パラメータ
            top_p: Top-p サンプリング
            top_k: Top-k サンプリング
            do_sample: サンプリング使用フラグ
            num_return_sequences: 生成シーケンス数
            stream: ストリーミング生成フラグ
            
        Returns:
            生成されたテキスト
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        start_time = time.time()
        
        try:
            # 生成パラメータ
            generation_kwargs = {
                "max_length": max_length,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "do_sample": do_sample,
                "num_return_sequences": num_return_sequences,
                "pad_token_id": self.tokenizer.eos_token_id,
                "return_full_text": False
            }
            
            if stream:
                return self._generate_stream(prompt, **generation_kwargs)
            else:
                # 通常生成
                outputs = self.pipeline(prompt, **generation_kwargs)
                
                if isinstance(outputs, list) and len(outputs) > 0:
                    response = outputs[0]["generated_text"]
                else:
                    response = ""
                
                # 統計更新
                end_time = time.time()
                self._update_inference_stats(prompt, response, end_time - start_time)
                
                return response
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error: {str(e)}"
    
    def _generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """ストリーミング生成"""
        try:
            # ストリーミング実装
            # 注意: transformersのpipelineは直接ストリーミングをサポートしていないため
            # トークンごとの生成を実装
            
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if self.device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            with torch.no_grad():
                for i in range(kwargs.get("max_length", 100)):
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=1,
                        temperature=kwargs.get("temperature", 0.7),
                        top_p=kwargs.get("top_p", 0.9),
                        top_k=kwargs.get("top_k", 50),
                        do_sample=kwargs.get("do_sample", True),
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                    
                    # 新しいトークンを取得
                    new_token = outputs[0, -1:]
                    new_text = self.tokenizer.decode(new_token, skip_special_tokens=True)
                    
                    yield new_text
                    
                    # 終了条件チェック
                    if new_token.item() == self.tokenizer.eos_token_id:
                        break
                    
                    # 次の入力を準備
                    inputs = {"input_ids": outputs}
                    
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            yield f"Error: {str(e)}"
    
    async def generate_response_async(self, prompt: str, **kwargs) -> str:
        """非同期テキスト生成"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.generate_response, 
            prompt, 
            **kwargs
        )
    
    def start_worker(self):
        """ワーカースレッド開始"""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("QwQ inference worker started")
    
    def stop_worker(self):
        """ワーカースレッド停止"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        logger.info("QwQ inference worker stopped")
    
    def _worker_loop(self):
        """ワーカーループ"""
        while self.is_running:
            try:
                # リクエスト取得（タイムアウト付き）
                request = self.request_queue.get(timeout=1.0)
                
                # 推論実行
                prompt = request["prompt"]
                kwargs = request.get("kwargs", {})
                request_id = request["id"]
                
                response = self.generate_response(prompt, **kwargs)
                
                # レスポンス送信
                self.response_queue.put({
                    "id": request_id,
                    "response": response,
                    "status": "success"
                })
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
                self.response_queue.put({
                    "id": request.get("id", "unknown"),
                    "response": f"Error: {str(e)}",
                    "status": "error"
                })
    
    def submit_request(self, prompt: str, **kwargs) -> str:
        """リクエスト送信"""
        request_id = f"req_{int(time.time() * 1000)}"
        
        self.request_queue.put({
            "id": request_id,
            "prompt": prompt,
            "kwargs": kwargs
        })
        
        return request_id
    
    def get_response(self, request_id: str, timeout: float = 30.0) -> Optional[Dict]:
        """レスポンス取得"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=1.0)
                if response["id"] == request_id:
                    return response
                else:
                    # 他のレスポンスは戻す
                    self.response_queue.put(response)
            except queue.Empty:
                continue
        
        return None
    
    def _update_inference_stats(self, prompt: str, response: str, duration: float):
        """推論統計更新"""
        prompt_tokens = len(self.tokenizer.encode(prompt))
        response_tokens = len(self.tokenizer.encode(response))
        total_tokens = prompt_tokens + response_tokens
        
        self.inference_stats['total_requests'] += 1
        self.inference_stats['total_tokens'] += total_tokens
        self.inference_stats['total_time'] += duration
        
        if self.inference_stats['total_time'] > 0:
            self.inference_stats['average_tokens_per_second'] = (
                self.inference_stats['total_tokens'] / self.inference_stats['total_time']
            )
        
        self._update_memory_stats()
    
    def _update_memory_stats(self):
        """メモリ統計更新"""
        process = psutil.Process()
        self.inference_stats['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        stats = self.inference_stats.copy()
        stats['model_loaded'] = self.is_loaded
        stats['device'] = self.device
        stats['quantization'] = self.quantization
        
        if torch.cuda.is_available():
            stats['gpu_memory_allocated'] = torch.cuda.memory_allocated() / 1024 / 1024  # MB
            stats['gpu_memory_reserved'] = torch.cuda.memory_reserved() / 1024 / 1024  # MB
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        try:
            if not self.is_loaded:
                return {"status": "unhealthy", "reason": "Model not loaded"}
            
            # 簡単な推論テスト
            test_prompt = "Hello"
            start_time = time.time()
            response = self.generate_response(test_prompt, max_length=10)
            duration = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": duration,
                "test_response": response[:50] + "..." if len(response) > 50 else response
            }
            
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e)}
    
    def save_config(self, config_path: str):
        """設定保存"""
        config = {
            "model_name": self.model_name,
            "device": self.device,
            "quantization": self.quantization,
            "max_memory": self.max_memory
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def load_config(cls, config_path: str) -> 'QwQInferenceEngine':
        """設定読み込み"""
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        return cls(**config)


# グローバルインスタンス
_qwq_engine = None

def get_qwq_engine() -> QwQInferenceEngine:
    """QwQ推論エンジンのシングルトンインスタンス取得"""
    global _qwq_engine
    if _qwq_engine is None:
        _qwq_engine = QwQInferenceEngine()
    return _qwq_engine

def initialize_qwq_engine(config: Optional[Dict] = None) -> bool:
    """QwQ推論エンジン初期化"""
    global _qwq_engine
    
    if config:
        _qwq_engine = QwQInferenceEngine(**config)
    else:
        _qwq_engine = QwQInferenceEngine()
    
    success = _qwq_engine.load_model()
    if success:
        _qwq_engine.start_worker()
    
    return success

def shutdown_qwq_engine():
    """QwQ推論エンジン終了"""
    global _qwq_engine
    if _qwq_engine:
        _qwq_engine.stop_worker()
        _qwq_engine.unload_model()
        _qwq_engine = None

