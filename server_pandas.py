import io
import os
import re
import glob

import pandas as pd

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("RSS")

# Load csv files
def load_csv_files(folder_path):
    """
    指定されたフォルダ内のすべてのCSVファイルを読み込み、
    ファイル名をローマ字に変換したデータフレーム名でグローバル変数として保存する
    
    Parameters:
    folder_path (str): CSVファイルが格納されているフォルダのパス
    
    Returns:
    dict: {元のファイル名: 作成されたデータフレーム名} の辞書
    """
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    created_dataframes = {}
    
    for csv_file in csv_files:
        # ファイル名を取得（拡張子なし）
        file_name = os.path.basename(csv_file)
        base_name = os.path.splitext(file_name)[0]
        
        # 拡張子無しをファイル名にする
        df_name = base_name
        
        # CSVファイルを読み込む
        try:
            df = pd.read_csv(csv_file)
            
            # 作成されたデータフレーム名を辞書に保存
            created_dataframes[base_name] = df
            print(f"読み込み成功: '{base_name}' → データフレーム名 '{df_name}'")
        except Exception as e:
            print(f"エラー: '{base_name}' の読み込みに失敗しました - {str(e)}")
    return created_dataframes

dfs = load_csv_files("./csv")


@mcp.tool()
def get_dataframe_names() -> str:
    """
    分析対象のDataframeの名称と説明の一覧を取得

    Returns:
    str: 分析対象のDataframeの名称の一覧
    """
    result = ""
    for i in dfs.keys():
        result = result + i + "\n"
    return result 

@mcp.tool()
def get_detailed_column_info(df_name : str) -> str:
    """
    指定したPandas Dataframeのカラム名とその統計情報を取得する
    
    Parameters:
    df_name : 対象のDataframeの名称
    
    Returns:
    str: カラム名と詳細情報を整形した文字列
    """
    # dfを取得
    if df_name not in dfs:
        return f"エラー: データフレーム '{df_name}' が見つかりません。"
    df = dfs[df_name]

    # カラム情報を取得
    columns_info = []
    
    for col_name in df.columns:
        dtype = df[col_name].dtype
        null_count = df[col_name].isna().sum()
        unique_count = df[col_name].nunique()
        
        if pd.api.types.is_numeric_dtype(dtype):
            min_val = df[col_name].min()
            max_val = df[col_name].max()
            info = f"- {col_name}: 型={dtype}, Null値={null_count}, ユニーク値={unique_count}, 最小値={min_val}, 最大値={max_val}"
        else:
            info = f"- {col_name}: 型={dtype}, Null値={null_count}, ユニーク値={unique_count}"
        
        columns_info.append(info)
    
    # データフレームの基本情報
    basic_info = f"行数: {len(df)}, 列数: {len(df.columns)}"
    
    # 整形された文字列を作成
    result = f"データフレームの基本情報: {basic_info}\n\nカラム詳細:\n" + "\n".join(columns_info)
    return result

@mcp.tool()
def select_dataframe(df_name : str, df_query : str, columns : list) -> str:
    """
    指定したPandas Dataframeに対して、絞り込み条件としてquery関数を適用し、その結果のDataframeの先頭10行と要約統計量を取得

    Parameters:
    df_name: 対象にするDataframeの名称
    df_query: 対象のDataFrameに対するquery関数の引数（例：age == 24 | point > 80 & state == "CA" & name.str.contains("太郎")）
    columns: 対象のDataFrameの出力に含めるcolumns。文字列の配列で与える

    Returns:
    str: query関数を適用したデータフレームの詳細情報を整形した文字列
    """
    if df_name not in dfs:
        return f"エラー: データフレーム '{df_name}' が見つかりません。"

    original_df = dfs[df_name]
    original_rows, original_cols = original_df.shape

    try:
        queried_df = original_df.query(df_query)
    except Exception as e:
        return f"エラー: クエリの実行に失敗しました - {str(e)}"


    # データフレームのサイズを確認
    total_rows, total_cols = queried_df.shape
    row_info = f"（元の{original_rows}行から絞り込み、結果 {total_rows}行）"
    col_info = f"（全{total_cols}列）"

    # データフレームの文字列表現を取得 (表示行数を制限する例)
    buffer = io.StringIO()
    # to_stringのオプションで表示行数などを制御できます
    queried_df[columns].to_string(buf=buffer, index=True, max_rows=100) # 例: 最大10行を表示
    df_str = buffer.getvalue()

    result = (
        f"# データフレーム情報 {row_info} {col_info}\n\n"
        f"## データ (先頭10行)\n\n{df_str}\n\n\n" # 表示行数制限を明記
        )

    # 数値カラムの要約統計量
    numeric_cols = queried_df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        summary = queried_df[numeric_cols].describe().T
        buffer = io.StringIO()
        summary.to_string(buf=buffer)
        summary_str = buffer.getvalue()
        result += f"\n## 数値カラムの要約統計量\n\n{summary_str}\n"
    else:
        result += "\n## 数値カラムの要約統計量\n(数値型のカラムがありません)"
    return result

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
