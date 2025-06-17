"""
Secure Configuration Management

Docker Secrets、HashiCorp Vault、AWS Secrets Managerに対応した
セキュアな機密情報管理システム
"""

import os
import json
import base64
import logging
from typing import Dict, Any, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets

logger = logging.getLogger(__name__)

class SecretManager:
    """機密情報管理クラス"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        初期化
        
        Args:
            encryption_key: 暗号化キー（指定されない場合は環境変数から取得）
        """
        self.encryption_key = encryption_key or os.getenv('ENCRYPTION_KEY')
        if not self.encryption_key:
            # 新しい暗号化キーを生成
            self.encryption_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            logger.warning("No encryption key provided, generated new key")
        
        self.fernet = self._create_fernet(self.encryption_key)
        
        # 設定プロバイダーの優先順位
        self.providers = [
            self._get_from_docker_secrets,
            self._get_from_vault,
            self._get_from_aws_secrets,
            self._get_from_env_file,
            self._get_from_environment
        ]
    
    def _create_fernet(self, key: str) -> Fernet:
        """Fernetインスタンスを作成"""
        try:
            # キーが既にbase64エンコードされている場合
            return Fernet(key.encode())
        except:
            # キーをPBKDF2でハッシュ化
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'devin_ai_clone_salt',  # 本番環境では動的なsaltを使用
                iterations=100000,
            )
            key_bytes = kdf.derive(key.encode())
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            return Fernet(fernet_key)
    
    def encrypt_value(self, value: str) -> str:
        """値を暗号化"""
        encrypted = self.fernet.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """値を復号化"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            raise ValueError("Failed to decrypt value")
    
    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        機密情報を取得
        
        優先順位:
        1. Docker Secrets
        2. HashiCorp Vault
        3. AWS Secrets Manager
        4. .env ファイル
        5. 環境変数
        """
        for provider in self.providers:
            try:
                value = provider(key)
                if value is not None:
                    logger.debug(f"Secret '{key}' found via {provider.__name__}")
                    return value
            except Exception as e:
                logger.debug(f"Provider {provider.__name__} failed for key '{key}': {e}")
                continue
        
        logger.warning(f"Secret '{key}' not found in any provider, using default")
        return default
    
    def _get_from_docker_secrets(self, key: str) -> Optional[str]:
        """Docker Secretsから取得"""
        secret_path = f"/run/secrets/{key}"
        if os.path.exists(secret_path):
            with open(secret_path, 'r') as f:
                return f.read().strip()
        return None
    
    def _get_from_vault(self, key: str) -> Optional[str]:
        """HashiCorp Vaultから取得"""
        vault_addr = os.getenv('VAULT_ADDR')
        vault_token = os.getenv('VAULT_TOKEN')
        vault_path = os.getenv('VAULT_SECRET_PATH', 'secret/devin-ai-clone')
        
        if not all([vault_addr, vault_token]):
            return None
        
        try:
            import hvac
            
            client = hvac.Client(url=vault_addr, token=vault_token)
            if not client.is_authenticated():
                logger.error("Vault authentication failed")
                return None
            
            response = client.secrets.kv.v2.read_secret_version(
                path=vault_path
            )
            
            secrets_data = response['data']['data']
            return secrets_data.get(key)
            
        except ImportError:
            logger.debug("hvac library not available for Vault integration")
            return None
        except Exception as e:
            logger.error(f"Vault error: {e}")
            return None
    
    def _get_from_aws_secrets(self, key: str) -> Optional[str]:
        """AWS Secrets Managerから取得"""
        secret_name = os.getenv('AWS_SECRET_NAME', 'devin-ai-clone-secrets')
        region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=region
            )
            
            response = client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            
            return secret_data.get(key)
            
        except ImportError:
            logger.debug("boto3 library not available for AWS Secrets Manager")
            return None
        except ClientError as e:
            logger.error(f"AWS Secrets Manager error: {e}")
            return None
        except Exception as e:
            logger.error(f"AWS Secrets Manager unexpected error: {e}")
            return None
    
    def _get_from_env_file(self, key: str) -> Optional[str]:
        """.envファイルから取得"""
        env_file = os.getenv('ENV_FILE', '.env')
        
        if not os.path.exists(env_file):
            return None
        
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or '=' not in line:
                        continue
                    
                    env_key, env_value = line.split('=', 1)
                    if env_key.strip() == key:
                        # 引用符を除去
                        value = env_value.strip().strip('"').strip("'")
                        return value
            
        except Exception as e:
            logger.error(f"Error reading .env file: {e}")
        
        return None
    
    def _get_from_environment(self, key: str) -> Optional[str]:
        """環境変数から取得"""
        return os.getenv(key)
    
    def set_secret(self, key: str, value: str, encrypt: bool = True) -> bool:
        """
        機密情報を設定（開発環境用）
        
        Args:
            key: キー
            value: 値
            encrypt: 暗号化するかどうか
        """
        try:
            if encrypt:
                encrypted_value = self.encrypt_value(value)
                # 暗号化された値を環境変数に設定
                os.environ[f"{key}_ENCRYPTED"] = encrypted_value
            else:
                os.environ[key] = value
            
            logger.info(f"Secret '{key}' set successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set secret '{key}': {e}")
            return False
    
    def get_database_config(self) -> Dict[str, str]:
        """データベース設定を取得"""
        return {
            'host': self.get_secret('DB_HOST', 'localhost'),
            'port': self.get_secret('DB_PORT', '5432'),
            'database': self.get_secret('DB_NAME', 'devin_ai_clone'),
            'username': self.get_secret('DB_USER', 'postgres'),
            'password': self.get_secret('DB_PASSWORD', ''),
            'ssl_mode': self.get_secret('DB_SSL_MODE', 'prefer')
        }
    
    def get_redis_config(self) -> Dict[str, str]:
        """Redis設定を取得"""
        return {
            'host': self.get_secret('REDIS_HOST', 'localhost'),
            'port': self.get_secret('REDIS_PORT', '6379'),
            'password': self.get_secret('REDIS_PASSWORD', ''),
            'db': self.get_secret('REDIS_DB', '0')
        }
    
    def get_jwt_config(self) -> Dict[str, str]:
        """JWT設定を取得"""
        return {
            'secret_key': self.get_secret('JWT_SECRET_KEY', secrets.token_urlsafe(32)),
            'algorithm': self.get_secret('JWT_ALGORITHM', 'HS256'),
            'access_token_expire_minutes': int(self.get_secret('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30')),
            'refresh_token_expire_days': int(self.get_secret('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7'))
        }
    
    def get_ai_model_config(self) -> Dict[str, str]:
        """AIモデル設定を取得"""
        return {
            'model_path': self.get_secret('QWEN_MODEL_PATH', '/models/qwen-4b'),
            'api_key': self.get_secret('OPENAI_API_KEY', ''),
            'api_base': self.get_secret('OPENAI_API_BASE', 'https://api.openai.com/v1'),
            'max_tokens': int(self.get_secret('AI_MAX_TOKENS', '2048')),
            'temperature': float(self.get_secret('AI_TEMPERATURE', '0.7'))
        }
    
    def get_git_config(self) -> Dict[str, str]:
        """Git設定を取得"""
        return {
            'default_branch': self.get_secret('GIT_DEFAULT_BRANCH', 'main'),
            'commit_author_name': self.get_secret('GIT_AUTHOR_NAME', 'Devin AI Clone'),
            'commit_author_email': self.get_secret('GIT_AUTHOR_EMAIL', 'devin@ai-clone.local')
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """設定の妥当性を検証"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 必須設定の確認
        required_secrets = [
            'JWT_SECRET_KEY',
            'DB_PASSWORD'
        ]
        
        for secret in required_secrets:
            value = self.get_secret(secret)
            if not value:
                validation_results['valid'] = False
                validation_results['errors'].append(f"Required secret '{secret}' is missing")
        
        # 推奨設定の確認
        recommended_secrets = [
            'ENCRYPTION_KEY',
            'REDIS_PASSWORD'
        ]
        
        for secret in recommended_secrets:
            value = self.get_secret(secret)
            if not value:
                validation_results['warnings'].append(f"Recommended secret '{secret}' is missing")
        
        # 設定値の妥当性確認
        try:
            jwt_expire = int(self.get_secret('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
            if jwt_expire < 5 or jwt_expire > 1440:  # 5分〜24時間
                validation_results['warnings'].append("JWT access token expiration time should be between 5 and 1440 minutes")
        except ValueError:
            validation_results['errors'].append("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a valid integer")
        
        return validation_results


# グローバルシークレットマネージャー
secret_manager = None

def init_secret_manager(encryption_key: Optional[str] = None) -> SecretManager:
    """シークレットマネージャーを初期化"""
    global secret_manager
    secret_manager = SecretManager(encryption_key)
    return secret_manager

def get_secret_manager() -> SecretManager:
    """シークレットマネージャーを取得"""
    global secret_manager
    if secret_manager is None:
        secret_manager = SecretManager()
    return secret_manager

# 便利関数
def get_secret(key: str, default: Any = None) -> Any:
    """機密情報を取得する便利関数"""
    return get_secret_manager().get_secret(key, default)

def get_database_url() -> str:
    """データベースURLを構築"""
    config = get_secret_manager().get_database_config()
    
    if config['password']:
        return f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}?sslmode={config['ssl_mode']}"
    else:
        return f"postgresql://{config['username']}@{config['host']}:{config['port']}/{config['database']}?sslmode={config['ssl_mode']}"

def get_redis_url() -> str:
    """Redis URLを構築"""
    config = get_secret_manager().get_redis_config()
    
    if config['password']:
        return f"redis://:{config['password']}@{config['host']}:{config['port']}/{config['db']}"
    else:
        return f"redis://{config['host']}:{config['port']}/{config['db']}"

