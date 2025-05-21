# MCP Server for table data (CSS)

Claude Desktop用のMCP Serverで、長大なCSVファイルの分析を支援するためのツールを提供します。

## 大雑把な使い方

https://modelcontextprotocol.io/quickstart/server 
のPython verが動く状態にする

1. csvフォルダに分析したいCSVファイルを入れる。ここにあるものだけが利用される
2. claude_desktop_config.json のmcp serverの名前をデータに応じてそれっぽく変更し、パスを絶対パスにする。Claude Desktopの設定ファイルとしてしかるべき場所に配置する
3. Claude Desktopを起動する
4. （任意）dbの場合はtable_info.txtというファイルが作られ、ここを直接編集することで使われないテーブルやカラムを設定できる


## 概要

このプロジェクトには2つの異なるサーバー実装が含まれています：

1. **server_pandas.py** - CSVファイルをPandas DataFrameとして直接メモリ上で操作します
2. **server_db.py** - CSVファイルをSQLiteデータベースに読み込み、SQLクエリで操作します

## 必要条件

- Python 3.10以上
- 必要なパッケージ（`pyproject.toml`に記載）

## インストール方法

```bash
# 依存関係のインストール
pip3 install -e .
```

SQLiteは標準でPythonに組み込まれているため、別途インストールする必要はありません。

## 使用方法

### Pandas版サーバーの起動

```bash
python server_pandas.py
```

### SQLite版サーバーの起動

```bash
python server_db.py
```

サーバー起動時に、`./csv/`ディレクトリ内のCSVファイルが自動的に読み込まれます。

## 機能

### Pandas版 (`server_pandas.py`)

1. **get_dataframe_names()** - 利用可能なPandas DataFrameの一覧を取得
2. **get_detailed_column_info(df_name)** - 指定したDataFrameのカラム情報と統計情報を取得
3. **select_dataframe(df_name, df_query, columns)** - 指定したDataFrameに対してクエリを実行し、結果を取得

### SQLite版 (`server_db.py`)

1. **get_table_names()** - データベース内のテーブル一覧を取得
2. **get_table_schema(table_name)** - 指定したテーブルのスキーマ情報を取得
3. **execute_sql_query(sql_query)** - SELECTクエリを実行して結果を取得（最大10行）

## 注意事項

- SQLite版は冪等性を確保するため、サーバー起動時に毎回テーブルを新規作成します
- セキュリティ上の理由から、SQLite版ではSELECTクエリのみ実行可能です
- 結果表示は最大10行に制限されています

## データセット

`./csv/`ディレクトリにCSVファイルを配置。Pandas Dataframeで特に設定しないで読み込めるものであればなんでもOk
