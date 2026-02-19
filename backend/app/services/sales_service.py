from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta
from app.models.sales import SalesTransaction

class SalesService:
    """販売データ分析サービス"""
    
    @staticmethod
    def get_daily_summary(db: Session, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """日別売上サマリーを取得"""
        query = db.query(
            func.date(SalesTransaction.transaction_date).label("date"),
            SalesTransaction.store_code,
            func.sum(SalesTransaction.total_price).label("total_sales"),
            func.sum(SalesTransaction.gross_profit).label("gross_profit"),
            func.count(SalesTransaction.id).label("transaction_count")
        )
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        return query.group_by(
            func.date(SalesTransaction.transaction_date),
            SalesTransaction.store_code
        ).all()
    
    @staticmethod
    def get_product_summary(db: Session, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """商品別売上サマリーを取得"""
        query = db.query(
            SalesTransaction.product_code,
            SalesTransaction.product_name,
            func.sum(SalesTransaction.quantity).label("total_quantity"),
            func.sum(SalesTransaction.total_price).label("total_sales"),
            func.sum(SalesTransaction.gross_profit).label("total_gross_profit")
        )
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        return query.group_by(
            SalesTransaction.product_code,
            SalesTransaction.product_name
        ).all()
    
    @staticmethod
    def get_store_summary(db: Session, start_date: datetime = None, end_date: datetime = None):
        """店舗別売上サマリーを取得"""
        query = db.query(
            SalesTransaction.store_code,
            func.sum(SalesTransaction.total_price).label("total_sales"),
            func.sum(SalesTransaction.gross_profit).label("total_gross_profit"),
            func.count(SalesTransaction.id).label("transaction_count")
        )
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        return query.group_by(SalesTransaction.store_code).all()
    
    @staticmethod
    def get_staff_list(db: Session, store_code: str = None):
        """スタッフ一覧を取得"""
        query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.store_code
        ).distinct()
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        return query.order_by(SalesTransaction.staff_name).all()
    
    @staticmethod
    def get_staff_performance(db: Session, staff_id: str = None, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """スタッフ別の成績サマリーを取得（サービス種別ごと）"""
        
        # 集計対象のサービス種別定義
        services_count_only = [
            'auMNP',
            'UQMNP',
            '店頭設定サポート',
            '機種変更',
            'クレジットカード',
            'ゴールドランクアップ',
            '新規ゴールド',
            'auひかり',
            '固定事業者トスアップ',
        ]
        
        services_gross_profit = ['au+1Collection']
        
        query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.product_name,
            func.count(SalesTransaction.id).label("count"),
            func.sum(SalesTransaction.gross_profit).label("gross_profit"),
            func.sum(SalesTransaction.total_price).label("total_sales")
        )
        
        if staff_id:
            query = query.filter(SalesTransaction.staff_id == staff_id)
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        results = query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.product_name
        ).all()
        
        return results
    
    @staticmethod
    def aggregate_staff_performance(db: Session, staff_id: str = None, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """スタッフ別の集計済み成績を取得（MNP対応版）"""
        
        # MNP関連のサービスカテゴリ定義
        # auMNP, UQMNP の場合はカウント数のみ
        # au+1Collection の場合は粗利額のみ
        count_only_services = [
            'auMNP(端末あり)',
            'auMNP(SIM単体)',
            'UQMNP(端末あり)',
            'UQMNP(SIM単体)',
            'au店頭設定サポート',
            '機種変更',
            'au-SIM単体販売',
            'UQ-SIM単体販売',
        ]
        
        gross_profit_services = [
            'au+1Collection'
        ]
        
        # サービスカテゴリごとに集計するクエリを作成
        query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.service_category,
            func.count(SalesTransaction.id).label("count"),
            func.sum(SalesTransaction.gross_profit).label("gross_profit"),
            func.sum(SalesTransaction.total_price).label("total_sales")
        )
        
        if staff_id:
            query = query.filter(SalesTransaction.staff_id == staff_id)
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        results = query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.service_category
        ).all()
        
        # スタッフごとに集計結果を整形
        staff_data = {}
        
        for result in results:
            staff_key = result.staff_id
            service_name = result.service_category or 'その他'
            
            if staff_key not in staff_data:
                staff_data[staff_key] = {
                    'staff_id': result.staff_id,
                    'staff_name': result.staff_name,
                    'services': {},
                    'total_sales': 0,
                    'total_gross_profit': 0
                }
            
            # サービス別の集計
            if service_name not in staff_data[staff_key]['services']:
                staff_data[staff_key]['services'][service_name] = {
                    'count': 0,
                    'gross_profit': 0
                }
            
            staff_data[staff_key]['services'][service_name]['count'] += result.count or 0
            staff_data[staff_key]['services'][service_name]['gross_profit'] += result.gross_profit or 0
            
            # 合計を更新
            staff_data[staff_key]['total_sales'] += result.total_sales or 0
            staff_data[staff_key]['total_gross_profit'] += result.gross_profit or 0
        
        return list(staff_data.values())
    
    @staticmethod
    def get_au_plus_one_collection_summary(db: Session, staff_id: str = None, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """au+1Collection実績サマリーを取得"""
        
        query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            func.count(SalesTransaction.id).label("transaction_count"),
            func.sum(SalesTransaction.total_price).label("total_sales"),
            func.sum(SalesTransaction.gross_profit).label("gross_profit")
        ).filter(SalesTransaction.large_category == 'au+1 Collection')
        
        if staff_id:
            query = query.filter(SalesTransaction.staff_id == staff_id)
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        results = query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name
        ).order_by(SalesTransaction.staff_name).all()
        
        return results
    
    @staticmethod
    def get_au_plus_one_collection_detail(db: Session, staff_id: str = None, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """au+1Collection詳細情報を取得（商品別）"""
        
        query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.product_name,
            SalesTransaction.small_category,
            func.count(SalesTransaction.id).label("transaction_count"),
            func.sum(SalesTransaction.total_price).label("total_sales"),
            func.sum(SalesTransaction.gross_profit).label("gross_profit")
        ).filter(SalesTransaction.large_category == 'au+1 Collection')
        
        if staff_id:
            query = query.filter(SalesTransaction.staff_id == staff_id)
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        results = query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.product_name,
            SalesTransaction.small_category
        ).order_by(SalesTransaction.staff_name, SalesTransaction.product_name).all()
        
        return results
    
    @staticmethod
    def get_au_plus_one_collection_by_category(db: Session, staff_id: str = None, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """au+1Collection中分類別集計を取得"""
        
        query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.small_category,
            func.count(SalesTransaction.id).label("transaction_count"),
            func.sum(SalesTransaction.total_price).label("total_sales"),
            func.sum(SalesTransaction.gross_profit).label("gross_profit")
        ).filter(SalesTransaction.large_category == 'au+1 Collection')
        
        if staff_id:
            query = query.filter(SalesTransaction.staff_id == staff_id)
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        results = query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            SalesTransaction.small_category
        ).order_by(SalesTransaction.staff_name, SalesTransaction.small_category).all()
        
        return results
    
    @staticmethod
    def get_au_plus_one_collection_daily(db: Session, staff_id: str = None, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """au+1Collection日別推移を取得"""
        
        query = db.query(
            func.date(SalesTransaction.transaction_date).label("date"),
            func.count(SalesTransaction.id).label("transaction_count"),
            func.sum(SalesTransaction.total_price).label("total_sales"),
            func.sum(SalesTransaction.gross_profit).label("gross_profit")
        ).filter(SalesTransaction.large_category == 'au+1 Collection')
        
        if staff_id:
            query = query.filter(SalesTransaction.staff_id == staff_id)
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        results = query.group_by(
            func.date(SalesTransaction.transaction_date)
        ).order_by(func.date(SalesTransaction.transaction_date)).all()
        
        return results
    
    @staticmethod
    def get_smartphone_sales_summary(db: Session, staff_id: str = None, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """スマートフォン販売（移動機 + iPhone/スマートフォン）の集計を取得"""
        
        query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            func.sum(SalesTransaction.quantity).label("total_quantity"),
            func.sum(SalesTransaction.gross_profit).label("total_gross_profit"),
            func.sum(SalesTransaction.total_price).label("total_sales")
        ).filter(
            SalesTransaction.large_category == '移動機',
            SalesTransaction.small_category.in_(['iPhone', 'スマートフォン'])
        )
        
        if staff_id:
            query = query.filter(SalesTransaction.staff_id == staff_id)
        
        if store_code:
            query = query.filter(SalesTransaction.store_code == store_code)
        
        if start_date:
            query = query.filter(SalesTransaction.transaction_date >= start_date)
        
        if end_date:
            query = query.filter(SalesTransaction.transaction_date <= end_date)
        
        results = query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name
        ).order_by(SalesTransaction.staff_name).all()
        
        return results

    @staticmethod
    def get_unit_price_per_smartphone(db: Session, staff_id: str = None, store_code: str = None, start_date: datetime = None, end_date: datetime = None):
        """
        スマートフォン台当たり単価を計算
        = au+1 Collection粗利総額 ÷ (大分類='移動機' かつ 小分類='スマートフォン'または'iPhone')台数
        """
        
        # au+1 Collection の粗利を取得
        au1_query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            func.sum(SalesTransaction.gross_profit).label("au1_gross_profit")
        ).filter(SalesTransaction.large_category == 'au+1 Collection')
        
        if staff_id:
            au1_query = au1_query.filter(SalesTransaction.staff_id == staff_id)
        if store_code:
            au1_query = au1_query.filter(SalesTransaction.store_code == store_code)
        if start_date:
            au1_query = au1_query.filter(SalesTransaction.transaction_date >= start_date)
        if end_date:
            au1_query = au1_query.filter(SalesTransaction.transaction_date <= end_date)
        
        au1_results = au1_query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name
        ).all()
        
        # スマートフォンの台数を取得
        smartphone_query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            func.sum(SalesTransaction.quantity).label("smartphone_count")
        ).filter(
            SalesTransaction.large_category == '移動機',
            SalesTransaction.small_category == 'スマートフォン'
        )
        
        if staff_id:
            smartphone_query = smartphone_query.filter(SalesTransaction.staff_id == staff_id)
        if store_code:
            smartphone_query = smartphone_query.filter(SalesTransaction.store_code == store_code)
        if start_date:
            smartphone_query = smartphone_query.filter(SalesTransaction.transaction_date >= start_date)
        if end_date:
            smartphone_query = smartphone_query.filter(SalesTransaction.transaction_date <= end_date)
        
        smartphone_results = smartphone_query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name
        ).all()
        
        # iPhoneの台数を取得
        iphone_query = db.query(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name,
            func.sum(SalesTransaction.quantity).label("iphone_count")
        ).filter(
            SalesTransaction.large_category == '移動機',
            SalesTransaction.small_category == 'iPhone'
        )
        
        if staff_id:
            iphone_query = iphone_query.filter(SalesTransaction.staff_id == staff_id)
        if store_code:
            iphone_query = iphone_query.filter(SalesTransaction.store_code == store_code)
        if start_date:
            iphone_query = iphone_query.filter(SalesTransaction.transaction_date >= start_date)
        if end_date:
            iphone_query = iphone_query.filter(SalesTransaction.transaction_date <= end_date)
        
        iphone_results = iphone_query.group_by(
            SalesTransaction.staff_id,
            SalesTransaction.staff_name
        ).all()
        
        # 結果を統合
        combined_results = []
        au1_map = {(r.staff_id, r.staff_name): r.au1_gross_profit for r in au1_results}
        smartphone_map = {(r.staff_id, r.staff_name): r.smartphone_count for r in smartphone_results}
        iphone_map = {(r.staff_id, r.staff_name): r.iphone_count for r in iphone_results}
        
        # 両方のデータを持つスタッフをフィルタ
        all_staff = set(au1_map.keys()) | set(smartphone_map.keys()) | set(iphone_map.keys())
        
        for staff_id_val, staff_name_val in all_staff:
            au1_profit = au1_map.get((staff_id_val, staff_name_val), 0) or 0
            smartphone_count = smartphone_map.get((staff_id_val, staff_name_val), 0) or 0
            iphone_count = iphone_map.get((staff_id_val, staff_name_val), 0) or 0
            total_device_count = smartphone_count + iphone_count
            
            # 台当たり単価を計算
            unit_price = 0
            if total_device_count and total_device_count > 0:
                unit_price = float(au1_profit) / float(total_device_count)
            
            combined_results.append({
                'staff_id': staff_id_val,
                'staff_name': staff_name_val,
                'au1_gross_profit': float(au1_profit) if au1_profit else 0,
                'smartphone_count': int(smartphone_count) if smartphone_count else 0,
                'iphone_count': int(iphone_count) if iphone_count else 0,
                'unit_price': round(unit_price, 0)  # 小数点以下四捨五入
            })
        
        # スタッフ名でソート
        combined_results.sort(key=lambda x: x['staff_name'])
        return combined_results
