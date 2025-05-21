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

def create_tables_from_csv(folder_path):
    """
    指定されたフォルダ内のすべてのCSVファイルを読み込み、
    SQLiteデータベースに同名のテーブルを作成する
    
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
            # 一旦pandasでCSVを読み込む（データ型を推測するため）
            df = pd.read_csv(csv_file)
            
            # 既存のテーブルを削除（冪等性の確保）
            cursor.execute(f"DROP TABLE IF EXISTS [{table_name}]")
            
            # CSVからSQLiteテーブルを作成
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            # テーブルのカラム情報を取得
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = cursor.fetchall()
            
            # テーブル情報を保存
            column_info = []
            for col in columns:
                column_info.append(f"- {col[1]}: 型={col[2]}")
            
            table_info.append(f"# テーブル: {table_name}")
            table_info.append(f"カラム数: {len(columns)}")
            table_info.append("カラム詳細:")
            table_info.extend(column_info)
            table_info.append("\n")
            
            # 作成されたテーブル名を保存
            created_tables.append(table_name)
            print(f"テーブル作成成功: '{base_name}' → テーブル名 '{table_name}'")
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
        )
        
        conn.close()
        return result
    except Exception as e:
        return f"エラー: SQLクエリの実行に失敗しました - {str(e)}"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')