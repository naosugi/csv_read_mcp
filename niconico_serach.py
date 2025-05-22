import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from mcp.server.fastmcp import FastMCP

# MCPサーバーを作成
mcp = FastMCP("NicovideoAPI")

class NicovideoAPIClient:
    """ニコニコ動画検索APIクライアント"""
    
    BASE_URL = "https://snapshot.search.nicovideo.jp/api/v2/snapshot/video/contents/search"
    VERSION_URL = "https://snapshot.search.nicovideo.jp/api/v2/snapshot/version"
    
    # 利用可能なフィールド
    AVAILABLE_FIELDS = [
        "contentId", "title", "description", "userId", "channelId",
        "viewCounter", "mylistCounter", "likeCounter", "lengthSeconds",
        "thumbnailUrl", "startTime", "lastResBody", "commentCounter",
        "lastCommentTime", "categoryTags", "tags", "genre"
    ]
    
    # ソート可能なフィールド
    SORTABLE_FIELDS = [
        "viewCounter", "mylistCounter", "likeCounter", "lengthSeconds",
        "startTime", "commentCounter", "lastCommentTime"
    ]
    
    @staticmethod
    def _make_request(url: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """APIリクエストを実行"""
        if headers is None:
            headers = {"User-Agent": "NicovideoMCP/1.0"}
        
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            return {"error": f"APIリクエストエラー: {str(e)}"}
    
    @staticmethod
    def _build_filters(filters_dict: Dict[str, Any]) -> str:
        """フィルタ条件をクエリパラメータに変換"""
        filter_params = []
        
        for field, conditions in filters_dict.items():
            if isinstance(conditions, dict):
                for operator, value in conditions.items():
                    if operator in ['gte', 'lte', 'gt', 'lt']:
                        filter_params.append(f"filters[{field}][{operator}]={urllib.parse.quote(str(value))}")
                    elif operator.isdigit():  # インデックス指定の場合
                        filter_params.append(f"filters[{field}][{operator}]={urllib.parse.quote(str(value))}")
            elif isinstance(conditions, list):
                for i, value in enumerate(conditions):
                    filter_params.append(f"filters[{field}][{i}]={urllib.parse.quote(str(value))}")
            else:
                filter_params.append(f"filters[{field}][0]={urllib.parse.quote(str(conditions))}")
        
        return "&".join(filter_params)
    
    @staticmethod
    def _format_results(data: Dict[str, Any]) -> str:
        """結果をフォーマット"""
        if "error" in data:
            return f"エラー: {data['error']}"
        
        meta = data.get("meta", {})
        
        if meta.get("status") != 200:
            error_code = meta.get("errorCode", "UNKNOWN")
            error_message = meta.get("errorMessage", "不明なエラー")
            return f"APIエラー: {error_code} - {error_message}"
        
        total_count = meta.get("totalCount", 0)
        videos = data.get("data", [])
        
        result = f"# 検索結果\n\n"
        result += f"- 総ヒット件数: {total_count:,}\n"
        result += f"- 取得件数: {len(videos)}\n"
        result += f"- リクエストID: {meta.get('id', 'N/A')}\n\n"
        
        for i, video in enumerate(videos, 1):
            result += f"## 動画 {i}\n"
            
            # 基本情報
            if 'contentId' in video:
                result += f"- **動画ID**: {video['contentId']}\n"
                result += f"- **URL**: https://nico.ms/{video['contentId']}\n"
            
            if 'title' in video:
                result += f"- **タイトル**: {video['title']}\n"
            
            if 'description' in video and video['description']:
                # 説明文を150文字で切り詰め
                desc = video['description'][:150] + "..." if len(video['description']) > 150 else video['description']
                result += f"- **説明**: {desc}\n"
            
            # 統計情報
            if 'viewCounter' in video:
                result += f"- **再生数**: {video['viewCounter']:,}\n"
            
            if 'mylistCounter' in video:
                result += f"- **マイリスト数**: {video['mylistCounter']:,}\n"
            
            if 'likeCounter' in video:
                result += f"- **いいね数**: {video['likeCounter']:,}\n"
            
            if 'commentCounter' in video:
                result += f"- **コメント数**: {video['commentCounter']:,}\n"
            
            # 時間情報
            if 'lengthSeconds' in video:
                minutes = video['lengthSeconds'] // 60
                seconds = video['lengthSeconds'] % 60
                result += f"- **再生時間**: {minutes}:{seconds:02d}\n"
            
            if 'startTime' in video:
                result += f"- **投稿日時**: {video['startTime']}\n"
            
            # その他の情報
            if 'tags' in video and video['tags']:
                result += f"- **タグ**: {video['tags']}\n"
            
            if 'genre' in video and video['genre']:
                result += f"- **ジャンル**: {video['genre']}\n"
            
            if 'thumbnailUrl' in video:
                result += f"- **サムネイル**: {video['thumbnailUrl']}\n"
            
            result += "\n"
        
        return result

@mcp.tool()
def search_nicovideo(
    q: str,
    targets: str = "title,description,tags",
    fields: Optional[str] = None,
    sort_field: str = "viewCounter",
    sort_order: str = "desc",
    limit: int = 10,
    offset: int = 0,
    view_count_min: Optional[int] = None,
    view_count_max: Optional[int] = None,
    mylist_count_min: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    genre: Optional[str] = None
) -> str:
    """
    ニコニコ動画を検索する
    
    Parameters:
    q: 検索キーワード
    targets: 検索対象（title,description,tags,tagsExact）
    fields: 取得するフィールド（カンマ区切り、未指定時はデフォルト）
    sort_field: ソートフィールド（viewCounter,mylistCounter,startTime等）
    sort_order: ソート順（desc=降順,asc=昇順）
    limit: 取得件数（最大100）
    offset: 取得開始位置（最大100,000）
    view_count_min: 最小再生数
    view_count_max: 最大再生数
    mylist_count_min: 最小マイリスト数
    date_from: 投稿日時の開始（YYYY-MM-DD形式）
    date_to: 投稿日時の終了（YYYY-MM-DD形式）
    genre: ジャンル
    
    Returns:
    str: 検索結果
    """
    # デフォルトフィールドを設定
    if fields is None:
        fields = "contentId,title,description,viewCounter,mylistCounter,likeCounter,commentCounter,lengthSeconds,startTime,tags,genre,thumbnailUrl"
    
    # パラメータ構築
    params = {
        "q": q,
        "targets": targets,
        "fields": fields,
        "_limit": min(max(limit, 1), 100),
        "_offset": min(max(offset, 0), 100000),
        "_context": "NicovideoMCP"
    }
    
    # ソート設定
    sort_prefix = "-" if sort_order.lower() == "desc" else "+"
    if sort_field in NicovideoAPIClient.SORTABLE_FIELDS:
        params["_sort"] = f"{sort_prefix}{sort_field}"
    
    # フィルタ構築
    filters = {}
    if view_count_min is not None:
        filters.setdefault("viewCounter", {})["gte"] = view_count_min
    if view_count_max is not None:
        filters.setdefault("viewCounter", {})["lte"] = view_count_max
    if mylist_count_min is not None:
        filters.setdefault("mylistCounter", {})["gte"] = mylist_count_min
    if genre:
        filters["genre"] = [genre]
    
    # 日付フィルタ
    if date_from:
        filters.setdefault("startTime", {})["gte"] = f"{date_from}T00:00:00+09:00"
    if date_to:
        filters.setdefault("startTime", {})["lt"] = f"{date_to}T23:59:59+09:00"
    
    # URLを構築
    query_params = urllib.parse.urlencode(params, encoding='utf-8')
    if filters:
        filter_params = NicovideoAPIClient._build_filters(filters)
        query_params += "&" + filter_params
    
    url = f"{NicovideoAPIClient.BASE_URL}?{query_params}"
    
    # リクエスト実行
    data = NicovideoAPIClient._make_request(url)
    return NicovideoAPIClient._format_results(data)

@mcp.tool()
def search_popular_nicovideo(
    q: str,
    days_back: int = 30,
    min_views: int = 10000,
    limit: int = 20
) -> str:
    """
    人気のニコニコ動画を検索する（便利関数）
    
    Parameters:
    q: 検索キーワード
    days_back: 何日前からの動画を対象にするか（デフォルト30日）
    min_views: 最小再生数（デフォルト10,000）
    limit: 取得件数（デフォルト20）
    
    Returns:
    str: 人気動画の検索結果
    """
    # 日付範囲を計算
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    date_from = start_date.strftime("%Y-%m-%d")
    
    return search_nicovideo(
        q=q,
        targets="title,description,tags",
        sort_field="viewCounter",
        sort_order="desc",
        limit=limit,
        view_count_min=min_views,
        date_from=date_from
    )

@mcp.tool()
def search_recent_nicovideo(
    q: str,
    days_back: int = 7,
    sort_by: str = "startTime",
    limit: int = 15
) -> str:
    """
    最近投稿されたニコニコ動画を検索する
    
    Parameters:
    q: 検索キーワード
    days_back: 何日前からの動画を対象にするか（デフォルト7日）
    sort_by: ソート基準（startTime=投稿日時, viewCounter=再生数）
    limit: 取得件数（デフォルト15）
    
    Returns:
    str: 最近の動画検索結果
    """
    # 日付範囲を計算
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    date_from = start_date.strftime("%Y-%m-%d")
    
    return search_nicovideo(
        q=q,
        targets="title,description,tags",
        sort_field=sort_by,
        sort_order="desc",
        limit=limit,
        date_from=date_from
    )

@mcp.tool()
def search_nicovideo_by_tag(
    tag: str,
    exact_match: bool = True,
    sort_field: str = "viewCounter",
    sort_order: str = "desc",
    limit: int = 10,
    min_views: Optional[int] = None
) -> str:
    """
    タグでニコニコ動画を検索する
    
    Parameters:
    tag: 検索するタグ
    exact_match: 完全一致検索を行うか（True=完全一致, False=部分一致）
    sort_field: ソートフィールド
    sort_order: ソート順（desc=降順,asc=昇順）
    limit: 取得件数
    min_views: 最小再生数
    
    Returns:
    str: タグ検索結果
    """
    targets = "tagsExact" if exact_match else "tags"
    
    return search_nicovideo(
        q=tag,
        targets=targets,
        sort_field=sort_field,
        sort_order=sort_order,
        limit=limit,
        view_count_min=min_views
    )

@mcp.tool()
def search_nicovideo_advanced(
    q: str,
    targets: str = "title,description,tags",
    fields: Optional[str] = None,
    view_range: Optional[tuple] = None,
    mylist_range: Optional[tuple] = None,
    length_range: Optional[tuple] = None,
    date_range: Optional[tuple] = None,
    genres: Optional[List[str]] = None,
    sort_field: str = "viewCounter",
    sort_order: str = "desc",
    limit: int = 10,
    offset: int = 0
) -> str:
    """
    高度な条件でニコニコ動画を検索する
    
    Parameters:
    q: 検索キーワード
    targets: 検索対象
    fields: 取得フィールド
    view_range: 再生数範囲 (min, max)
    mylist_range: マイリスト数範囲 (min, max)
    length_range: 再生時間範囲（秒） (min, max)
    date_range: 投稿日範囲 (start_date, end_date) YYYY-MM-DD形式
    genres: ジャンルリスト
    sort_field: ソートフィールド
    sort_order: ソート順
    limit: 取得件数
    offset: オフセット
    
    Returns:
    str: 高度検索結果
    """
    if fields is None:
        fields = "contentId,title,description,viewCounter,mylistCounter,likeCounter,commentCounter,lengthSeconds,startTime,tags,genre,thumbnailUrl"
    
    params = {
        "q": q,
        "targets": targets,
        "fields": fields,
        "_limit": min(max(limit, 1), 100),
        "_offset": min(max(offset, 0), 100000),
        "_context": "NicovideoMCP"
    }
    
    # ソート設定
    sort_prefix = "-" if sort_order.lower() == "desc" else "+"
    if sort_field in NicovideoAPIClient.SORTABLE_FIELDS:
        params["_sort"] = f"{sort_prefix}{sort_field}"
    
    # フィルタ構築
    filters = {}
    
    if view_range:
        if view_range[0] is not None:
            filters.setdefault("viewCounter", {})["gte"] = view_range[0]
        if view_range[1] is not None:
            filters.setdefault("viewCounter", {})["lte"] = view_range[1]
    
    if mylist_range:
        if mylist_range[0] is not None:
            filters.setdefault("mylistCounter", {})["gte"] = mylist_range[0]
        if mylist_range[1] is not None:
            filters.setdefault("mylistCounter", {})["lte"] = mylist_range[1]
    
    if length_range:
        if length_range[0] is not None:
            filters.setdefault("lengthSeconds", {})["gte"] = length_range[0]
        if length_range[1] is not None:
            filters.setdefault("lengthSeconds", {})["lte"] = length_range[1]
    
    if date_range:
        if date_range[0]:
            filters.setdefault("startTime", {})["gte"] = f"{date_range[0]}T00:00:00+09:00"
        if date_range[1]:
            filters.setdefault("startTime", {})["lt"] = f"{date_range[1]}T23:59:59+09:00"
    
    if genres:
        filters["genre"] = genres
    
    # URLを構築
    query_params = urllib.parse.urlencode(params, encoding='utf-8')
    if filters:
        filter_params = NicovideoAPIClient._build_filters(filters)
        query_params += "&" + filter_params
    
    url = f"{NicovideoAPIClient.BASE_URL}?{query_params}"
    
    # リクエスト実行
    data = NicovideoAPIClient._make_request(url)
    return NicovideoAPIClient._format_results(data)

@mcp.tool()
def get_nicovideo_api_version() -> str:
    """
    ニコニコ動画検索APIのデータ更新日時を取得する
    
    Returns:
    str: データ更新日時情報
    """
    data = NicovideoAPIClient._make_request(NicovideoAPIClient.VERSION_URL)
    
    if "error" in data:
        return f"エラー: {data['error']}"
    
    last_modified = data.get("last_modified", "不明")
    
    result = f"# ニコニコ動画検索API データ更新情報\n\n"
    result += f"- 最終更新日時: {last_modified}\n"
    result += f"- 更新頻度: 毎日AM5:00（日本標準時）\n"
    result += f"- 注意: 更新作業により、実際に参照可能になる時間は遅れる場合があります\n"
    
    return result

if __name__ == "__main__":
    # MCPサーバーを起動
    mcp.run(transport='stdio')