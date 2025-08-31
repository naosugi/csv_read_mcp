"""
レファレンス協同データベース MCP Server - 機能完全版
Complete Functional Implementation for Japanese Library Reference Database
"""

from mcp.server.fastmcp import FastMCP
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple, Union
import json
from datetime import datetime, timedelta
import re
from enum import Enum

# MCP Server initialization
mcp = FastMCP("レファレンス協同データベース - 機能完全版", description="""
日本全国の図書館が蓄積した50万件超のレファレンス事例・調べ方マニュアル・特別コレクションを検索するMCPツール

効果的な使用のため、最初に get_search_guidance() を呼び出してガイダンスを確認してください。

主な機能：
- 段階的検索ガイダンス（get_search_guidance）
- 統合検索（unified_search） - 全データタイプ対応
- レファレンス事例検索（search_references）
- 調べ方マニュアル検索（search_manuals）
- 特別コレクション検索（search_collections）
- 参加館プロファイル検索（search_library_profiles）
- トレンド分析（analyze_trends）
- 研究ギャップ発見（discover_research_gaps）
""")

# データタイプ定義
class DataType(Enum):
    REFERENCE = "reference"  # レファレンス事例
    MANUAL = "manual"  # 調べ方マニュアル
    COLLECTION = "collection"  # 特別コレクション
    PROFILE = "profile"  # 参加館プロファイル
    ALL = "all"  # 全種別

# ユーザータイプ定義
class UserType(Enum):
    LIBRARIAN = "librarian"  # 図書館員
    RESEARCHER = "researcher"  # 研究者
    STUDENT = "student"  # 学生
    GENERAL = "general"  # 一般利用者
    EDUCATOR = "educator"  # 教育関係者
    BUSINESS = "business"  # ビジネス

# 段階的検索ガイダンス（表記ゆれ処理をAIに委ねる版）
SEARCH_GUIDANCE = """
# レファレンス協同データベース検索AI向け完全ガイダンス

## 重要：表記ゆれ処理について

**AIが自動的に表記ゆれを生成してください。**
同じ概念の異なる表現を検索する際は、AIが以下のパターンを考慮して複数の検索を実行してください：

### 表記ゆれパターン例
- 技術用語: AI → 人工知能、エーアイ、artificial intelligence、機械学習、ディープラーニング
- 外来語: データベース → DB、database、データ・ベース
- 施設名: 図書館 → ライブラリー、library、図書室、メディアセンター
- 人物分類: 子供 → 子ども、児童、幼児、小児、キッズ、年少者
- カタカナ/ひらがな: コンピュータ → コンピューター、こんぴゅーた
- 略語/正式名: スマホ → スマートフォン、smartphone、携帯電話

**実装方法**: 
1. ユーザーのクエリから主要概念を抽出
2. AIが関連する表記ゆれを生成（3-5パターン）
3. 各パターンで順次検索を実行
4. 結果を統合して重複を除去

## データタイプ別検索ガイド

### 1. レファレンス事例 (type=reference)
**用途**: 実際の質問と回答、調査プロセスを検索
**検索フィールド**:
- question: 質問文
- answer: 回答内容
- ans-proc: 調査プロセス
- bibl-desc: 参考資料
- solution: 解決状態（resolved/unresolved）
- applause-num: 拍手数（品質指標）

**ユースケース例**:
- 類似質問の発見
- 調査手法の学習
- 未解決問題の特定

### 2. 調べ方マニュアル (type=manual)
**用途**: テーマ別の体系的な調査手法ガイド
**検索フィールド**:
- theme: テーマ
- keyword: キーワード
- completion: 完成状態（complete/incomplete）

**ユースケース例**:
- 探究学習の教材作成
- 調査手法の標準化
- 情報リテラシー教育

### 3. 特別コレクション (type=collection)
**用途**: 図書館の特色ある資料群情報
**検索フィールド**:
- col-name: コレクション名
- origin: 由来・経緯
- feature: 特徴
- catalog: 目録情報

**ユースケース例**:
- 地域資料の発見
- 専門資料の所在確認
- デジタルアーカイブ連携

### 4. 参加館プロファイル (type=profile)
**用途**: 図書館の特徴・サービス情報
**検索フィールド**:
- lib-name: 図書館名
- lib-group: 種別（public/academic/special/school）
- feature: 特徴
- service: サービス内容

**ユースケース例**:
- 専門図書館の発見
- 地域図書館の比較
- 連携先の探索

## 段階的検索フローチャート

```
START → クエリ分析 → データタイプ判定
    ↓
適切なデータタイプを選択
    ├─ 質問・調査系 → reference
    ├─ 手法・ガイド系 → manual
    ├─ 資料・所蔵系 → collection
    └─ 図書館情報系 → profile
    ↓
Phase 1: 厳密検索（完全一致）
    └─ ヒット少 → Phase 2へ
    ↓
Phase 2: AIによる表記ゆれ展開
    └─ 複数パターンで検索
    ↓
Phase 3: フィールド拡張
    └─ question → answer → ans-proc → anywhere
    ↓
Phase 4: 品質/時期でフィルタリング
    └─ 必要に応じて絞り込み
    ↓
結果統合・分析 → 次の戦略提案
```

## CQL検索構文リファレンス

### 基本演算子
- `=` : 完全一致
- `all` : AND検索（全て含む）
- `any` : OR検索（いずれか含む）
- `not` : NOT検索（除外）
- `>=`, `<=` : 数値範囲指定

### 共通検索フィールド
- `anywhere` : 全項目横断検索
- `keyword` : キーワード
- `reg-date` : 登録日
- `lst-date` : 最終更新日
- `lib-name` : 図書館名
- `lib-group` : 図書館種別

### データタイプ別特有フィールド

#### reference（レファレンス事例）
- `question` : 質問文
- `answer` : 回答
- `ans-proc` : 調査プロセス
- `bibl-desc` : 参考資料
- `solution` : 解決状態
- `applause-num` : 拍手数
- `access-num` : アクセス数
- `ptn-type` : 利用者タイプ
- `con-type` : 内容種別

#### manual（調べ方マニュアル）
- `theme` : テーマ
- `completion` : 完成状態
- `scope` : 対象範囲

#### collection（特別コレクション）
- `col-name` : コレクション名
- `origin` : 由来
- `feature` : 特徴
- `catalog` : 目録
- `restriction` : 利用制限

#### profile（参加館プロファイル）
- `service` : サービス
- `feature` : 特徴
- `address` : 住所
- `tel` : 電話番号

## ユーザータイプ別推奨設定

### 図書館員（librarian）
- 優先データタイプ: reference, manual
- 品質フィルタ: applause-num >= 3
- ソート: 拍手数順
- 特記: 調査プロセス重視

### 研究者（researcher）
- 優先データタイプ: reference, collection
- 品質フィルタ: なし（未解決も含む）
- ソート: 登録日順
- 特記: 網羅性重視

### 学生（student）
- 優先データタイプ: manual, reference
- 品質フィルタ: solution=resolved
- ソート: アクセス数順
- 特記: わかりやすさ重視

### 一般利用者（general）
- 優先データタイプ: reference
- 品質フィルタ: solution=resolved
- ソート: アクセス数順
- 特記: 人気事例優先

### 教育関係者（educator）
- 優先データタイプ: manual, reference
- 品質フィルタ: completion=complete
- ソート: 拍手数順
- 特記: 教材として使える完成度

### ビジネス（business）
- 優先データタイプ: reference, profile
- 品質フィルタ: lib-group=special
- ソート: 最新順
- 特記: 専門図書館重視

## 実装上の重要ポイント

1. **表記ゆれはAIが処理**: 辞書に依存せず、AIが文脈に応じて適切な表記バリエーションを生成
2. **データタイプを適切に選択**: 質問の性質に応じて最適なデータタイプを選ぶ
3. **段階的拡張**: 厳密→表記ゆれ→フィールド拡張→フィルタリングの順で検索
4. **結果の統合**: 複数検索の結果を統合し、重複を除去
5. **次の戦略を提案**: 結果が不十分な場合は代替戦略を提示

このガイダンスに従って、ユーザーのニーズに最適な検索を実行してください。
"""

class XMLParser:
    """XML応答パーサー"""
    
    @staticmethod
    def parse_response(xml_content: str) -> Dict[str, Any]:
        """XMLレスポンスをパース"""
        try:
            # BOMを除去
            if xml_content.startswith('\ufeff'):
                xml_content = xml_content[1:]
            
            root = ET.fromstring(xml_content)
            
            # RSS形式
            if root.tag == 'rss':
                return XMLParser._parse_rss(root)
            # result_set形式
            elif root.tag == 'result_set':
                return XMLParser._parse_result_set(root)
            else:
                return {'error': f'Unknown XML format: {root.tag}'}
                
        except ET.ParseError as e:
            return {'error': f'XML parsing failed: {str(e)}'}
    
    @staticmethod
    def _parse_rss(root: ET.Element) -> Dict[str, Any]:
        """RSS形式のパース"""
        items = []
        for item in root.findall('.//item'):
            item_data = {}
            for child in item:
                if child.text:
                    item_data[child.tag] = child.text
            items.append(item_data)
        
        return {
            'format': 'rss',
            'total_items': len(items),
            'items': items
        }
    
    @staticmethod
    def _parse_result_set(root: ET.Element) -> Dict[str, Any]:
        """result_set形式のパース"""
        result = {
            'format': 'result_set',
            'hit_num': int(root.findtext('hit_num', '0')),
            'results_get_position': int(root.findtext('results_get_position', '1')),
            'results_num': int(root.findtext('results_num', '0')),
            'results_cd': root.findtext('results_cd', '0'),
            'items': []
        }
        
        # エラーチェック
        if result['results_cd'] != '0':
            error_items = []
            for err in root.findall('.//err_item'):
                error_items.append({
                    'code': err.findtext('err_code'),
                    'field': err.findtext('err_fld'),
                    'message': err.findtext('err_msg')
                })
            result['errors'] = error_items
            return result
        
        # 結果の処理
        for result_item in root.findall('.//result'):
            item_data = XMLParser._extract_item_data(result_item)
            result['items'].append(item_data)
        
        return result
    
    @staticmethod
    def _extract_item_data(element: ET.Element) -> Dict[str, Any]:
        """要素からデータを抽出"""
        data = {}
        for child in element:
            if len(child) > 0:
                data[child.tag] = XMLParser._extract_item_data(child)
            else:
                if child.text:
                    data[child.tag] = child.text
        return data

class APIClient:
    """レファレンス協同データベースAPIクライアント"""
    
    BASE_URL = "https://crd.ndl.go.jp/api/refsearch"
    
    @staticmethod
    def execute_search(query: str, data_type: str = "reference", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """API検索実行"""
        if params is None:
            params = {}
        
        # デフォルトパラメータ
        default_params = {
            'type': data_type,
            'results_num': 50
        }
        default_params.update(params)
        
        # CQLクエリ設定
        if query:
            default_params['query'] = query
        
        try:
            # リクエスト実行
            response = requests.get(
                APIClient.BASE_URL,
                params=default_params,
                timeout=30
            )
            response.raise_for_status()
            
            # XML解析
            return XMLParser.parse_response(response.text)
            
        except requests.exceptions.RequestException as e:
            return {'error': 'request_failed', 'message': str(e)}
        except Exception as e:
            return {'error': 'unexpected', 'message': str(e)}

# MCPツール実装

@mcp.tool()
def get_search_guidance() -> str:
    """
    レファレンス検索のベストプラクティスとガイダンスを取得
    
    Returns:
        段階的検索アプローチの完全ガイダンス（表記ゆれ処理はAI側で実施）
    
    **重要**: レファレンス検索を開始する前に、このツールを呼び出してガイダンスを確認してください。
    表記ゆれの処理方法、データタイプの選択方法、段階的検索の実行方法が含まれています。
    """
    return SEARCH_GUIDANCE

@mcp.tool()
def unified_search(
    query: str,
    data_types: Optional[List[str]] = None,
    user_type: str = "general",
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    全データタイプを横断した統合検索
    
    Parameters:
        query: 検索クエリ（自然言語）
        data_types: 検索対象データタイプのリスト ["reference", "manual", "collection", "profile"]
                   Noneの場合は全タイプ
        user_type: ユーザータイプ (librarian/researcher/student/general/educator/business)
        filters: 詳細フィルタ
            - solution: "resolved" or "unresolved" (referenceのみ)
            - completion: "complete" or "incomplete" (manualのみ)
            - lib_group: ["public", "academic", "special", "school"]
            - date_from: "YYYYMMDD"
            - date_to: "YYYYMMDD"
            - min_quality: 最小拍手数
    
    Returns:
        全データタイプの統合検索結果（JSON形式）
    """
    try:
        if data_types is None:
            data_types = ["reference", "manual", "collection", "profile"]
        
        if filters is None:
            filters = {}
        
        results = {
            'query': query,
            'user_type': user_type,
            'searched_types': data_types,
            'results_by_type': {},
            'total_hits': 0,
            'recommendations': []
        }
        
        # 各データタイプで検索
        for dtype in data_types:
            # CQLクエリ構築
            cql_parts = []
            
            # 基本クエリ
            if dtype == "reference":
                cql_parts.append(f'question any {query}')
                if filters.get('solution'):
                    cql_parts.append(f'solution={filters["solution"]}')
                if filters.get('min_quality'):
                    cql_parts.append(f'applause-num >= {filters["min_quality"]}')
            elif dtype == "manual":
                cql_parts.append(f'theme any {query}')
                if filters.get('completion'):
                    cql_parts.append(f'completion={filters["completion"]}')
            elif dtype == "collection":
                cql_parts.append(f'col-name any {query}')
            elif dtype == "profile":
                cql_parts.append(f'lib-name any {query}')
            
            # 共通フィルタ
            if filters.get('lib_group'):
                lib_groups = filters['lib_group'] if isinstance(filters['lib_group'], list) else [filters['lib_group']]
                cql_parts.append(f'lib-group any {" ".join(lib_groups)}')
            
            if filters.get('date_from'):
                cql_parts.append(f'reg-date >= {filters["date_from"]}')
            if filters.get('date_to'):
                cql_parts.append(f'reg-date <= {filters["date_to"]}')
            
            # CQL結合
            final_cql = ' and '.join(cql_parts) if cql_parts else f'anywhere any {query}'
            
            # 検索実行
            search_params = {'results_num': 30}
            if dtype == "reference" and user_type != "researcher":
                search_params['sort'] = 'applause-num'
                search_params['sort_order'] = 'desc'
            
            response = APIClient.execute_search(final_cql, dtype, search_params)
            
            # 結果格納
            results['results_by_type'][dtype] = {
                'hits': response.get('hit_num', 0),
                'items': response.get('items', [])[:10],  # 各タイプ上位10件
                'cql_query': final_cql
            }
            
            results['total_hits'] += response.get('hit_num', 0)
        
        # 推奨事項生成
        if results['total_hits'] == 0:
            results['recommendations'].append({
                'action': 'expand_query',
                'message': '結果が見つかりませんでした。より一般的な用語で検索するか、表記を変えて試してください。'
            })
        else:
            # 最も結果が多いデータタイプを特定
            best_type = max(results['results_by_type'].items(), 
                          key=lambda x: x[1]['hits'])[0]
            results['recommendations'].append({
                'action': 'focus_search',
                'message': f'{best_type}に最も関連する結果があります。このタイプに絞って詳細検索を推奨します。'
            })
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            'error': 'search_failed',
            'message': str(e)
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def search_references(
    query: str,
    solution_status: Optional[str] = None,
    quality_filter: Optional[int] = None,
    sort_by: str = "fit"
) -> str:
    """
    レファレンス事例の検索（詳細オプション付き）
    
    Parameters:
        query: 検索クエリ
        solution_status: 解決状態フィルタ ("resolved", "unresolved", None=両方)
        quality_filter: 最小拍手数
        sort_by: ソート基準 ("fit", "applause-num", "access-num", "reg-date")
    
    Returns:
        レファレンス事例検索結果（JSON形式）
    """
    try:
        # CQLクエリ構築
        cql_parts = [f'question any {query}']
        
        if solution_status:
            cql_parts.append(f'solution={solution_status}')
        if quality_filter:
            cql_parts.append(f'applause-num >= {quality_filter}')
        
        final_cql = ' and '.join(cql_parts)
        
        params = {
            'results_num': 50,
            'sort': sort_by,
            'sort_order': 'desc' if sort_by != 'fit' else 'asc'
        }
        
        response = APIClient.execute_search(final_cql, "reference", params)
        
        result = {
            'query': query,
            'filters': {
                'solution_status': solution_status,
                'quality_filter': quality_filter
            },
            'total_hits': response.get('hit_num', 0),
            'items': response.get('items', []),
            'cql_query': final_cql
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            'error': 'search_failed',
            'message': str(e)
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def search_manuals(
    theme: str,
    completion_status: Optional[str] = None
) -> str:
    """
    調べ方マニュアルの検索
    
    Parameters:
        theme: テーマ・トピック
        completion_status: 完成状態 ("complete", "incomplete", None=両方)
    
    Returns:
        調べ方マニュアル検索結果（JSON形式）
    """
    try:
        cql_parts = [f'theme any {theme}']
        
        if completion_status:
            cql_parts.append(f'completion={completion_status}')
        
        final_cql = ' and '.join(cql_parts)
        
        response = APIClient.execute_search(final_cql, "manual", {'results_num': 30})
        
        result = {
            'theme': theme,
            'completion_status': completion_status,
            'total_hits': response.get('hit_num', 0),
            'items': response.get('items', []),
            'cql_query': final_cql
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            'error': 'search_failed',
            'message': str(e)
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def search_collections(
    keyword: str,
    has_catalog: Optional[bool] = None
) -> str:
    """
    特別コレクションの検索
    
    Parameters:
        keyword: 検索キーワード
        has_catalog: 目録の有無でフィルタ
    
    Returns:
        特別コレクション検索結果（JSON形式）
    """
    try:
        cql_parts = [f'col-name any {keyword}']
        
        if has_catalog is not None:
            if has_catalog:
                cql_parts.append('catalog any 有')
            else:
                cql_parts.append('catalog not 有')
        
        final_cql = ' and '.join(cql_parts)
        
        response = APIClient.execute_search(final_cql, "collection", {'results_num': 30})
        
        result = {
            'keyword': keyword,
            'has_catalog': has_catalog,
            'total_hits': response.get('hit_num', 0),
            'items': response.get('items', []),
            'cql_query': final_cql
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            'error': 'search_failed',
            'message': str(e)
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def search_library_profiles(
    location: Optional[str] = None,
    library_type: Optional[str] = None,
    service_keyword: Optional[str] = None
) -> str:
    """
    参加館プロファイルの検索
    
    Parameters:
        location: 地域・場所
        library_type: 図書館種別 (public/academic/special/school)
        service_keyword: サービスに関するキーワード
    
    Returns:
        参加館プロファイル検索結果（JSON形式）
    """
    try:
        cql_parts = []
        
        if location:
            cql_parts.append(f'address any {location}')
        if library_type:
            cql_parts.append(f'lib-group={library_type}')
        if service_keyword:
            cql_parts.append(f'service any {service_keyword}')
        
        if not cql_parts:
            cql_parts = ['anywhere any 図書館']
        
        final_cql = ' and '.join(cql_parts)
        
        response = APIClient.execute_search(final_cql, "profile", {'results_num': 30})
        
        result = {
            'filters': {
                'location': location,
                'library_type': library_type,
                'service_keyword': service_keyword
            },
            'total_hits': response.get('hit_num', 0),
            'items': response.get('items', []),
            'cql_query': final_cql
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            'error': 'search_failed',
            'message': str(e)
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def analyze_trends(
    topic: str,
    date_from: str,
    date_to: str,
    data_type: str = "reference"
) -> str:
    """
    時系列トレンド分析
    
    Parameters:
        topic: 分析対象トピック
        date_from: 開始日（YYYYMMDD）
        date_to: 終了日（YYYYMMDD）
        data_type: データタイプ (reference/manual/collection/profile)
    
    Returns:
        トレンド分析結果（JSON形式）
    """
    try:
        # 期間を月単位で分割
        start = datetime.strptime(date_from, '%Y%m%d')
        end = datetime.strptime(date_to, '%Y%m%d')
        
        trend_data = []
        current = start
        
        while current <= end:
            next_month = current + timedelta(days=30)
            
            # 期間検索
            if data_type == "reference":
                period_cql = f'question any {topic}'
            elif data_type == "manual":
                period_cql = f'theme any {topic}'
            elif data_type == "collection":
                period_cql = f'col-name any {topic}'
            else:
                period_cql = f'anywhere any {topic}'
            
            period_cql += f' and reg-date >= {current.strftime("%Y%m%d")} and reg-date <= {next_month.strftime("%Y%m%d")}'
            
            response = APIClient.execute_search(period_cql, data_type, {'results_num': 100})
            
            trend_data.append({
                'period': current.strftime('%Y-%m'),
                'count': response.get('hit_num', 0),
                'sample_items': response.get('items', [])[:3]
            })
            
            current = next_month
        
        # 分析
        analysis = {
            'topic': topic,
            'data_type': data_type,
            'period': f'{date_from} - {date_to}',
            'trend_data': trend_data,
            'summary': {
                'total_count': sum(d['count'] for d in trend_data),
                'average_monthly': sum(d['count'] for d in trend_data) / len(trend_data) if trend_data else 0,
                'peak_month': max(trend_data, key=lambda x: x['count'])['period'] if trend_data else None
            }
        }
        
        return json.dumps(analysis, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            'error': 'trend_analysis_failed',
            'message': str(e)
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def discover_research_gaps(
    field: str,
    include_all_types: bool = True
) -> str:
    """
    研究ギャップと未解決課題の発見
    
    Parameters:
        field: 研究分野
        include_all_types: 全データタイプを対象にするか
    
    Returns:
        研究機会の分析結果（JSON形式）
    """
    try:
        gaps = {
            'field': field,
            'analysis_date': datetime.now().isoformat(),
            'findings': {}
        }
        
        # レファレンス事例の未解決率分析
        unsolved_cql = f'question any {field} and solution=unresolved'
        unsolved = APIClient.execute_search(unsolved_cql, "reference", {'results_num': 50})
        
        all_cql = f'question any {field}'
        all_refs = APIClient.execute_search(all_cql, "reference", {'results_num': 50})
        
        unsolved_count = unsolved.get('hit_num', 0)
        total_count = all_refs.get('hit_num', 0)
        
        gaps['findings']['reference_analysis'] = {
            'total_cases': total_count,
            'unsolved_cases': unsolved_count,
            'unsolved_rate': unsolved_count / total_count if total_count > 0 else 0,
            'sample_unsolved': unsolved.get('items', [])[:5]
        }
        
        # マニュアルの不完全率分析
        if include_all_types:
            incomplete_manual_cql = f'theme any {field} and completion=incomplete'
            incomplete = APIClient.execute_search(incomplete_manual_cql, "manual", {'results_num': 20})
            
            gaps['findings']['manual_analysis'] = {
                'incomplete_manuals': incomplete.get('hit_num', 0),
                'sample_incomplete': incomplete.get('items', [])[:3]
            }
            
            # コレクションのカバレッジ分析
            collection_cql = f'col-name any {field}'
            collections = APIClient.execute_search(collection_cql, "collection", {'results_num': 20})
            
            gaps['findings']['collection_coverage'] = {
                'available_collections': collections.get('hit_num', 0),
                'sample_collections': collections.get('items', [])[:3]
            }
        
        # 研究機会の提案
        opportunities = []
        
        if gaps['findings']['reference_analysis']['unsolved_rate'] > 0.3:
            opportunities.append({
                'type': 'high_unsolved_rate',
                'message': f'{field}分野は未解決率が{gaps["findings"]["reference_analysis"]["unsolved_rate"]:.1%}と高く、研究の余地があります'
            })
        
        if include_all_types and gaps['findings'].get('manual_analysis', {}).get('incomplete_manuals', 0) > 0:
            opportunities.append({
                'type': 'incomplete_guides',
                'message': f'{field}分野の調べ方マニュアルに未完成のものがあり、体系化の機会があります'
            })
        
        gaps['research_opportunities'] = opportunities
        
        return json.dumps(gaps, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            'error': 'gap_analysis_failed',
            'message': str(e)
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def get_database_status() -> str:
    """
    レファレンス協同データベースAPIの状態確認
    
    Returns:
        API接続状態と統計情報（JSON形式）
    """
    try:
        # 各データタイプでテスト
        test_results = {}
        
        for dtype in ["reference", "manual", "collection", "profile"]:
            test_response = APIClient.execute_search('anywhere any 図書館', dtype, {'results_num': 1})
            test_results[dtype] = {
                'operational': 'error' not in test_response,
                'sample_count': test_response.get('hit_num', 0)
            }
        
        status = {
            'database_info': {
                'name': 'レファレンス協同データベース（レファ協）',
                'operator': '国立国会図書館',
                'description': '全国900館以上の図書館による協同データベース',
                'data_types': {
                    'reference': 'レファレンス事例（約50万件）',
                    'manual': '調べ方マニュアル',
                    'collection': '特別コレクション',
                    'profile': '参加館プロファイル'
                }
            },
            'api_status': {
                'overall_operational': all(t['operational'] for t in test_results.values()),
                'data_type_status': test_results,
                'last_checked': datetime.now().isoformat()
            },
            'available_features': [
                '全データタイプ統合検索',
                'レファレンス事例の品質フィルタリング',
                '調べ方マニュアルの完成度別検索',
                '特別コレクションの目録有無フィルタ',
                '参加館の地域・種別検索',
                '時系列トレンド分析',
                '研究ギャップ発見'
            ]
        }
        
        return json.dumps(status, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            'error': 'status_check_failed',
            'message': str(e)
        }, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # MCPサーバー起動
    mcp.run()
