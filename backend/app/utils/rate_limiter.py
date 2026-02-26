from datetime import datetime, timedelta, timezone
from collections import defaultdict
import threading

class RateLimiter:
    """レート制限（ブルートフォース対策）"""
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_allowed(self, identifier: str) -> bool:
        """リクエストが許可されているか確認"""
        now = datetime.now(timezone.utc)
        
        with self.lock:
            # 期限切れの試行を削除
            cutoff_time = now - timedelta(seconds=self.window_seconds)
            self.attempts[identifier] = [
                attempt_time for attempt_time in self.attempts[identifier]
                if attempt_time > cutoff_time
            ]
            
            # 試行上限をチェック
            if len(self.attempts[identifier]) >= self.max_attempts:
                return False
            
            # 新しい試行を記録
            self.attempts[identifier].append(now)
            return True
    
    def get_remaining_time(self, identifier: str) -> int:
        """ブロックが解除されるまでの秒数"""
        if identifier not in self.attempts or len(self.attempts[identifier]) < self.max_attempts:
            return 0
        
        oldest_attempt = self.attempts[identifier][0]
        cutoff_time = oldest_attempt + timedelta(seconds=self.window_seconds)
        remaining = (cutoff_time - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))

# グローバルレート制限インスタンス
login_limiter = RateLimiter(max_attempts=5, window_seconds=300)  # 5分間に5回まで
api_limiter = RateLimiter(max_attempts=100, window_seconds=60)  # 1分間に100回まで
