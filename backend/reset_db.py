#!/usr/bin/env python
"""データベースをリセットするスクリプト"""
import os
from app.database import engine, Base
from app.models import SalesTransaction, User, Store

if __name__ == "__main__":
    # テーブルをすべて削除
    print("既存のテーブルを削除しています...")
    Base.metadata.drop_all(bind=engine)
    
    # 新しいテーブルを作成
    print("新しいテーブルを作成しています...")
    Base.metadata.create_all(bind=engine)
    
    print("データベースをリセットしました")
