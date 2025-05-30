import io
import os
import re
import glob
import sqlite3
import pandas as pd
import csv

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("RSS")

# SQLite database file
DB_PATH = "./rssystem.db"
# Text file for storing table information
TABLE_INFO_PATH = "./table_info.txt"

def has_leading_zeros(series):
    """
    列に先頭0がある文字列が含まれているかチェック
    
    Parameters:
    series: pandas Series
    
    Returns:
    bool: 先頭0がある文字列が含まれている場合True
    """
    for value in series:
        if isinstance(value, str) and value and len(value) > 1:
            # 数字のみで構成され、先頭が0で始まり、かつ"0"単体ではない場合
            if value.isdigit() and value[0] == '0':
                return True
    return False

def can_convert_to_numeric(series):
    """
    列が数値に変換可能かチェック
    
    Parameters:
    series: pandas Series
    
    Returns:
    bool: 数値変換可能な場合True
    """
    try:
        # 空文字列を除外してチェック
        non_empty = series[series != '']
        if len(non_empty) == 0:
            return False
        pd.to_numeric(non_empty)
        return True
    except:
        return False

def create_tables_from_csv(folder_path):
    """
    指定されたフォルダ内のすべてのCSVファイルを読み込み、
    SQLiteデータベースに同名のテーブルを作成する
    先頭0がある列は文字列、純粋な数値列は数値型として保存する
    
    Parameters:
    folder_path (str): CSVファイルが格納されているフォルダのパス
    
    Returns:
    list: 作成されたテーブル名のリスト
    """
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    created_tables = []
    
    # SQLiteデータベースに接続（存在しない場合は作成される）
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # テーブル情報をファイルに保存するための準備
    table_info = []
    
    for csv_file in csv_files:
        # ファイル名を取得（拡張子なし）
        file_name = os.path.basename(csv_file)
        base_name = os.path.splitext(file_name)[0]
        
        # テーブル名として使用
        table_name = base_name
        
        try:
            # まず全ての列を文字列として読み込み
            df_str = pd.read_csv(csv_file, dtype=str, keep_default_na=False)
            df_str = df_str.fillna('')
            
            # 各列のデータ型を決定
            column_types = {}
            for column in df_str.columns:
                if has_leading_zeros(df_str[column]):
                    # 先頭0がある場合は文字列として保持
                    column_types[column] = 'TEXT'
                elif can_convert_to_numeric(df_str[column]):
                    # 数値変換可能な場合は数値として扱う
                    column_types[column] = 'NUMERIC'
                else:
                    # その他は文字列
                    column_types[column] = 'TEXT'
            
            # 最終的なDataFrameを作成
            df_final = df_str.copy()
            for column, data_type in column_types.items():
                if data_type == 'NUMERIC':
                    # 空文字列をNaNに変換してから数値変換
                    df_final[column] = df_str[column].replace('', None)
                    df_final[column] = pd.to_numeric(df_final[column], errors='coerce')
            
            # 既存のテーブルを削除（冪等性の確保）
            cursor.execute(f"DROP TABLE IF EXISTS [{table_name}]")
            
            # CSVからSQLiteテーブルを作成
            df_final.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # テーブルのカラム情報を取得
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = cursor.fetchall()
            
            # テーブル情報を保存
            column_info = []
            for col in columns:
                col_name = col[1]
                sqlite_type = col[2]
                original_type = column_types.get(col_name, 'TEXT')
                
                if original_type == 'NUMERIC':
                    description = f"数値型 (SQLite: {sqlite_type})"
                else:
                    description = f"文字列型 (SQLite: {sqlite_type}) - 先頭0保持"
                
                column_info.append(f"- {col_name}: {description}")
            
            table_info.append(f"# テーブル: {table_name}")
            table_info.append(f"カラム数: {len(columns)}")
            table_info.append("カラム詳細:")
            table_info.extend(column_info)
            
            # サンプルデータを表示（先頭3行）
            sample_data = df_final.head(3)
            table_info.append("サンプルデータ（最初の3行）:")
            for idx, row in sample_data.iterrows():
                row_data = " | ".join([f"{col}: {val}" for col, val in row.items()])
                table_info.append(f"  行{idx + 1}: {row_data}")
            
            table_info.append("\n")
            
            # 作成されたテーブル名を保存
            created_tables.append(table_name)
            
            # データ型の判定結果を出力
            type_summary = []
            for col, dtype in column_types.items():
                type_summary.append(f"{col}({dtype})")
            
            print(f"テーブル作成成功: '{base_name}' → '{table_name}' [{', '.join(type_summary)}]")
            
        except Exception as e:
            print(f"エラー: '{base_name}' のテーブル作成に失敗しました - {str(e)}")
    
    # テーブル情報をファイルに保存
    with open(TABLE_INFO_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(table_info))
    
    conn.commit()
    conn.close()
    return created_tables

# CSVファイルからテーブルを作成
table_names = create_tables_from_csv("./csv")

@mcp.tool()
def get_table_names() -> str:
    """
    データベース内のテーブル名の一覧を取得
    
    Returns:
    str: 分析対象のテーブル名の一覧
    """
    # テキストファイルからテーブル情報を読み込む
    try:
        with open(TABLE_INFO_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # テーブル名を抽出（# テーブル: の後の部分）
        tables = re.findall(r'# テーブル: (.*)', content)
        return "\n".join(tables)
    except Exception as e:
        return f"エラー: テーブル情報の取得に失敗しました - {str(e)}"

@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """
    指定したテーブルのスキーマ情報を取得する
    
    Parameters:
    table_name: 対象のテーブル名
    
    Returns:
    str: テーブルのスキーマ情報を整形した文字列
    """
    # テキストファイルからテーブル情報を読み込む
    try:
        with open(TABLE_INFO_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 指定されたテーブルの情報を抽出
        pattern = f"# テーブル: {table_name}(.*?)(?=# テーブル:|$)"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            table_info = match.group(1).strip()
            return f"# テーブル: {table_name}\n{table_info}"
        else:
            return f"エラー: テーブル '{table_name}' の情報が見つかりません。"
    except Exception as e:
        return f"エラー: テーブル情報の取得に失敗しました - {str(e)}"

@mcp.tool()
def execute_sql_query(sql_query: str) -> str:
    """
    SQLクエリを実行して結果を取得する
    
    Parameters:
    sql_query: 実行するSQLクエリ（SELECTのみ許可）
    
    Returns:
    str: クエリ結果を整形した文字列
    """
    # クエリが SELECT で始まることを確認（セキュリティ対策）
    if not re.match(r'^\s*SELECT', sql_query, re.IGNORECASE):
        return "エラー: SELECTクエリのみ許可されています。"
    
    try:
        # データベースに接続
        conn = sqlite3.connect(DB_PATH)
        
        # クエリを実行
        result_df = pd.read_sql_query(sql_query, conn)
        
        # 結果の行数と列数を取得
        total_rows, total_cols = result_df.shape
        
        # 最大10行に制限
        limited_df = result_df.head(10)
        
        # データフレームの文字列表現を取得
        buffer = io.StringIO()
        limited_df.to_string(buf=buffer, index=True)
        df_str = buffer.getvalue()
        
        result = (
            f"# クエリ結果 (全{total_rows}行、表示は最大10行まで) (列数: {total_cols})\n\n"
            f"## データ\n\n{df_str}\n\n"
            f"注意: 先頭0がある列は文字列型、純粋な数値列は数値型として保存されています。\n"
            f"      文字列型の列で数値計算が必要な場合は CAST(column AS REAL) などで型変換してください。\n\n"
        )
        
        conn.close()
        return result
    except Exception as e:
        return f"エラー: SQLクエリの実行に失敗しました - {str(e)}"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')