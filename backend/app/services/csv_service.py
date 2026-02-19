import pandas as pd
from io import StringIO
from typing import List, Dict, Tuple
import chardet
from datetime import datetime
from app.schemas import SalesTransactionCreate

class MNPJudge:
    """MNP判定ロジック"""
    
    @staticmethod
    def judge_service_category(ticket_data: List[Dict]) -> Dict[str, str]:
        """
        同一伝票内の複数行からサービスカテゴリを判定
        ticket_data: 同一伝票番号の複数行のデータリスト
        Returns: {row_index: service_category, ...}
        """
        # 各行のサービスカテゴリを判定
        result = {}
        
        # 伝票内で手続区分とSIM/端末の情報を抽出
        has_procedure = False
        procedure_type = None  # 'MNP' or 'MNP3G' or '番号移行'
        has_device_au = False  # au関連端末ありか
        has_device_uq = False  # UQ関連端末ありか
        has_au_sim = False  # au-SIM or eSIM ありか
        has_uq_sim = False  # UQ-SIM ありか
        
        # 伝票内の全行をスキャン
        for idx, line_data in enumerate(ticket_data):
            large_cat = line_data.get('large_category', '')
            small_cat = line_data.get('small_category', '')
            procedure = line_data.get('procedure_name', '')
            
            # 手続区分を確認
            if procedure and pd.notna(procedure):
                if 'MNP' in procedure or '番号移行' in procedure:
                    has_procedure = True
                    if 'MNP' in procedure:
                        procedure_type = 'MNP'
            
            # 端末を確認
            if large_cat == '移動機' and small_cat:
                # au関連か判定
                if 'au' in str(line_data.get('product_name', '')).lower() or small_cat in ['iPhone', 'スマートフォン']:
                    has_device_au = True
                # UQ関連か判定
                if 'UQ' in str(line_data.get('product_name', '')).upper():
                    has_device_uq = True
            
            # SIMを確認
            if large_cat == 'SIM' and small_cat:
                if small_cat == 'au-SIM' or small_cat == 'eSIM':
                    has_au_sim = True
                elif small_cat == 'UQ-SIM' or small_cat == 'UQ-SIM2':
                    has_uq_sim = True
        
        # 各行に対してサービスカテゴリを割り当て
        for idx, line_data in enumerate(ticket_data):
            large_cat = line_data.get('large_category', '')
            small_cat = line_data.get('small_category', '')
            procedure = line_data.get('procedure_name', '')
            contract_type = line_data.get('お客様契約区分名', '')
            
            service_category = None
            
            # MNP判定
            if has_procedure:
                if contract_type == 'au':
                    if has_device_au and has_au_sim:
                        service_category = 'auMNP(端末あり)'
                    elif has_au_sim and not has_device_au:
                        service_category = 'auMNP(SIM単体)'
                elif contract_type == 'UQ':
                    if has_device_uq and has_uq_sim:
                        service_category = 'UQMNP(端末あり)'
                    elif has_uq_sim and not has_device_uq:
                        service_category = 'UQMNP(SIM単体)'
            
            # MNPでない場合は他のカテゴリで判定
            if not service_category:
                if large_cat == 'au+1 Collection':
                    service_category = 'au+1Collection'
                elif '店頭設定サポート' in small_cat:
                    service_category = 'au店頭設定サポート'
                elif '機種変更' in procedure:
                    service_category = '機種変更'
                elif large_cat == 'SIM':
                    if small_cat == 'au-SIM':
                        service_category = 'au-SIM単体販売'
                    elif small_cat == 'UQ-SIM':
                        service_category = 'UQ-SIM単体販売'
                else:
                    service_category = line_data.get('large_category', 'その他')
            
            result[idx] = service_category
        
        return result

class CSVService:
    """CSV ファイル解析サービス"""
    
    @staticmethod
    def detect_encoding(file_bytes: bytes) -> str:
        """
        ファイルのエンコーディングを自動検出
        """
        result = chardet.detect(file_bytes)
        encoding = result.get('encoding', 'utf-8')
        
        # 一般的なエンコーディングの正規化
        if encoding is None:
            encoding = 'utf-8'
        
        encoding_map = {
            'utf-8': 'utf-8',
            'UTF-8': 'utf-8',
            'shift_jis': 'shift_jis',
            'SHIFT_JIS': 'shift_jis',
            'cp932': 'cp932',
            'CP932': 'cp932',
            'euc_jp': 'euc_jp',
            'EUC_JP': 'euc_jp',
            'iso-2022-jp': 'iso-2022-jp',
        }
        
        # マッピングにない場合は小文字に正規化
        normalized = encoding_map.get(encoding, encoding.lower())
        return normalized

    @staticmethod
    def extract_store_info(file_bytes: bytes) -> List[Dict]:
        """
        CSVから店舗情報を抽出
        Returns: [{"store_code": "S002078", "store_name": "..."}]
        """
        try:
            # エンコーディング自動検出
            detected_encoding = CSVService.detect_encoding(file_bytes)
            
            # ファイルをデコード
            try:
                content_str = file_bytes.decode(detected_encoding)
            except (UnicodeDecodeError, LookupError):
                fallback_encodings = ['utf-8', 'shift_jis', 'cp932', 'euc_jp', 'latin-1']
                content_str = None
                
                for enc in fallback_encodings:
                    try:
                        content_str = file_bytes.decode(enc)
                        detected_encoding = enc
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content_str is None:
                    raise ValueError("サポートされているエンコーディングでファイルをデコードできません")
            
            # CSVを読み込み
            df = pd.read_csv(StringIO(content_str))
            
            # 店舗情報を抽出（重複排除）
            stores = []
            seen_codes = set()
            
            for idx, row in df.iterrows():
                try:
                    store_code = str(row.iloc[1]).strip() if len(row) > 1 else None
                    store_name = str(row.iloc[2]).strip() if len(row) > 2 else None
                    
                    if store_code and store_code != "" and store_code not in seen_codes and pd.notna(store_code):
                        seen_codes.add(store_code)
                        stores.append({
                            "store_code": store_code,
                            "store_name": store_name if store_name and store_name != "" else f"店舗 {store_code}",
                            "location": "未設定"
                        })
                except Exception as e:
                    print(f"[警告] 行{idx+2}での店舗情報抽出: {e}")
                    continue
            
            print(f"[CSV] {len(stores)}件の店舗情報を抽出")
            return stores
            
        except Exception as e:
            print(f"[警告] 店舗情報抽出失敗: {str(e)}")
            return []
    
    @staticmethod
    def parse_sales_csv(file_bytes: bytes) -> List[SalesTransactionCreate]:
        """
        販売データCSVを解析
        ファイルバイナリを受け取りエンコーディング自動検出してパース
        """
        try:
            # エンコーディング自動検出
            detected_encoding = CSVService.detect_encoding(file_bytes)
            print(f"[CSV] 検出されたエンコーディング: {detected_encoding}")
            
            # ファイルをデコード
            try:
                content_str = file_bytes.decode(detected_encoding)
            except (UnicodeDecodeError, LookupError) as e:
                print(f"[警告] {detected_encoding} でのデコード失敗: {e}")
                # 失敗した場合はフォールバック
                fallback_encodings = ['utf-8', 'shift_jis', 'cp932', 'euc_jp', 'latin-1']
                content_str = None
                
                for enc in fallback_encodings:
                    try:
                        content_str = file_bytes.decode(enc)
                        print(f"[成功] {enc} でのデコードに成功")
                        detected_encoding = enc
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content_str is None:
                    raise ValueError("サポートされているエンコーディングでファイルをデコードできません")
            
            # CSVを読み込み
            df = pd.read_csv(StringIO(content_str))
            
            print(f"[CSV] 検出カラム数: {len(df.columns)}")
            print(f"[CSV] 実際のカラム: {df.columns.tolist()[:10]}")  # 最初の10カラムをログに出力
            
            transactions = []
            
            # 実際のCSVファイル構造に合わせたマッピング
            # POS売上明細データの場合
            column_index_map = {
                'transaction_date': None,  # 複合カラム: 売上日付 + 売上時刻
                'store_code': 1,  # 統括拠点コード
                'product_code': 16,  # 商品コード
                'product_name': 17,  # POS表示商品名
                'quantity': 30,  # 数量
                'unit_price': 31,  # 販売単価（税込）
                'total_price': 32,  # 販売明細額（税込）
                'gross_profit': 73,  # 粗利（column 73）
                'staff_id': 57,  # 実績ユーザーID
                'staff_name_first': 58,  # 実績担当者姓
                'staff_name_last': 59,  # 実績担当者名
                'ticket_number': 7,  # 売上伝票番号
                'large_category': 21,  # 大分類名
                'small_category': 23,  # 中分類名
                'procedure_name': 48,  # 手続区分名
                'procedure_name_2': 50,  # 手続区分２名
                'contract_type': 64,  # お客様契約区分名
            }
            
            # 同一伝票番号ごとにグループ化してMNP判定を実施
            grouped_by_ticket = {}
            raw_data_map = {}
            
            for idx, row in df.iterrows():
                try:
                    ticket_num = str(row.iloc[7]).strip() if len(row) > 7 else f"UNKNOWN_{idx}"
                    
                    if ticket_num not in grouped_by_ticket:
                        grouped_by_ticket[ticket_num] = []
                        raw_data_map[ticket_num] = []
                    
                    # 行データを保存
                    line_data = {
                        'row_index': idx,
                        'large_category': str(row.iloc[21]).strip() if len(row) > 21 else '',
                        'small_category': str(row.iloc[23]).strip() if len(row) > 23 else '',
                        'procedure_name': str(row.iloc[48]).strip() if len(row) > 48 and pd.notna(row.iloc[48]) else '',
                        'product_name': str(row.iloc[17]).strip() if len(row) > 17 else '',
                        'お客様契約区分名': str(row.iloc[64]).strip() if len(row) > 64 else '',
                    }
                    
                    grouped_by_ticket[ticket_num].append(line_data)
                    raw_data_map[ticket_num].append(row)
                    
                except Exception as e:
                    print(f"[警告] 行{idx+2}: グループ化エラー: {e}")
                    continue
            
            # 各伝票についてMNP判定を実施
            ticket_service_categories = {}
            ticket_row_count = {}  # 伝票ごとの行カウント
            
            for ticket_num, line_data_list in grouped_by_ticket.items():
                service_categories = MNPJudge.judge_service_category(line_data_list)
                ticket_service_categories[ticket_num] = service_categories
                ticket_row_count[ticket_num] = len(line_data_list)  # 伝票の行数を記録
            
            # 伝票内での行番号をカウントするためのマップを作成
            ticket_row_index_map = {}
            for ticket_num in grouped_by_ticket.keys():
                ticket_row_index_map[ticket_num] = 0
            
            # トランザクション作成
            for idx, row in df.iterrows():
                try:
                    data = {}
                    
                    # 日付と時刻を組み合わせる
                    try:
                        date_str = str(row.iloc[4]).strip()  # 売上日付
                        time_str = str(row.iloc[5]).strip() if len(row) > 5 else "00:00:00"  # 売上時刻
                        combined_datetime = f"{date_str} {time_str}"
                        # 複数の日付フォーマットに対応
                        for fmt in ["%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d", "%Y%m%d %H:%M:%S"]:
                            try:
                                dt = datetime.strptime(combined_datetime, fmt)
                                data['transaction_date'] = dt
                                break
                            except ValueError:
                                continue
                        if 'transaction_date' not in data:
                            raise ValueError(f"日付形式が認識できません: {combined_datetime}")
                    except Exception as e:
                        print(f"[警告] 行{idx+2}: 日付パース失敗: {e}")
                        continue
                    
                    # その他のカラムをマッピング
                    data['store_code'] = str(row.iloc[1]).strip() if len(row) > 1 else ""
                    data['product_code'] = str(row.iloc[16]).strip() if len(row) > 16 else ""
                    data['product_name'] = str(row.iloc[17]).strip() if len(row) > 17 else ""
                    data['ticket_number'] = str(row.iloc[7]).strip() if len(row) > 7 else ""
                    data['large_category'] = str(row.iloc[21]).strip() if len(row) > 21 else ""
                    data['small_category'] = str(row.iloc[23]).strip() if len(row) > 23 else ""
                    data['procedure_name'] = str(row.iloc[48]).strip() if len(row) > 48 and pd.notna(row.iloc[48]) else ""
                    data['procedure_name_2'] = str(row.iloc[50]).strip() if len(row) > 50 and pd.notna(row.iloc[50]) else ""
                    
                    # 数値変換
                    try:
                        data['quantity'] = int(row.iloc[30]) if len(row) > 30 and pd.notna(row.iloc[30]) else 1
                    except:
                        data['quantity'] = 1
                    
                    try:
                        data['unit_price'] = float(row.iloc[31]) if len(row) > 31 and pd.notna(row.iloc[31]) else 0
                    except:
                        data['unit_price'] = 0
                    
                    try:
                        data['total_price'] = float(row.iloc[32]) if len(row) > 32 and pd.notna(row.iloc[32]) else 0
                    except:
                        data['total_price'] = 0
                    
                    try:
                        data['gross_profit'] = float(row.iloc[73]) if len(row) > 73 and pd.notna(row.iloc[73]) else 0
                    except:
                        data['gross_profit'] = 0
                    
                    # スタッフ情報（実績ユーザーを使用）
                    data['staff_id'] = str(row.iloc[57]).strip() if len(row) > 57 else ""
                    staff_first = str(row.iloc[58]).strip() if len(row) > 58 else ""
                    staff_last = str(row.iloc[59]).strip() if len(row) > 59 else ""
                    data['staff_name'] = f"{staff_first}{staff_last}".strip() if staff_first or staff_last else ""
                    
                    # サービスカテゴリを追加
                    ticket_num = data['ticket_number']
                    # 同じ伝票番号内での行番号を計算
                    if ticket_num in grouped_by_ticket:
                        row_line_index = len(grouped_by_ticket[ticket_num]) - 1
                    else:
                        row_line_index = 0
                    
                    if ticket_num in ticket_service_categories and row_line_index in ticket_service_categories[ticket_num]:
                        data['service_category'] = ticket_service_categories[ticket_num][row_line_index]
                    else:
                        data['service_category'] = 'その他'
                    
                    # スキーマバリデーション
                    transaction = SalesTransactionCreate(**data)
                    transactions.append(transaction)
                    
                except Exception as e:
                    print(f"[警告] 行{idx+2}: {e}")
                    continue
            
            print(f"[CSV] {len(transactions)}件のトランザクションを抽出")
            return transactions
            
        except Exception as e:
            raise ValueError(f"CSV解析失敗: {str(e)}")


