import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from mcp.server.fastmcp import FastMCP

# MCPサーバーを作成
mcp = FastMCP("NicovideoAPI")

class NicovideoAPIClient:
    """ニコニコ動画検索APIクライアント"""
    
    BASE_URL = "https://snapshot.search.nicovideo.jp/api/v2/snapshot/video/contents/search"
    VERSION_URL = "https://snapshot.search.nicovideo.jp/api/v2/snapshot/version"
    THUMBINFO_URL = "https://ext.nicovideo.jp/api/getthumbinfo/"
    RANKING_RSS_URL = "https://www.nicovideo.jp/ranking/genre/"
    
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
    
    # 利用可能なジャンル
    GENRES = [
        "all", "hot-topic", "entertainment", "radio", "music_sound",
        "dance", "animal", "nature", "cooking", "traveling_outdoor",
        "vehicle", "sports", "society_politics_news", "technology_craft",
        "commentary_lecture", "anime", "game", "other"
    ]
    
    # ランキング期間
    RANKING_TERMS = {
        "hour": "毎時",
        "24h": "24時間",
        "week": "週間",
        "month": "月間",
        "total": "合計"
    }
    
    @staticmethod
    def _make_request(url: str, headers: Dict[str, str] = None) -> Union[Dict[str, Any], str]:
        """APIリクエストを実行"""
        if headers is None:
            headers = {"User-Agent": "NicovideoMCP/1.0"}
        
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request) as response:
                content_type = response.headers.get('Content-Type', '')
                data = response.read().decode('utf-8')
                
                if 'json' in content_type:
                    return json.loads(data)
                else:
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
    
    @staticmethod
    def _parse_thumbinfo_xml(xml_data: str) -> Dict[str, Any]:
        """getthumbinfo APIのXMLレスポンスをパース"""
        try:
            root = ET.fromstring(xml_data)
            
            if root.get('status') == 'fail':
                error = root.find('.//error')
                if error is not None:
                    code = error.find('code').text if error.find('code') is not None else 'UNKNOWN'
                    desc = error.find('description').text if error.find('description') is not None else '不明なエラー'
                    return {"error": f"{code}: {desc}"}
                return {"error": "動画情報の取得に失敗しました"}
            
            thumb = root.find('.//thumb')
            if thumb is None:
                return {"error": "動画情報が見つかりません"}
            
            # 各要素を取得
            video_info = {}
            for child in thumb:
                if child.tag == 'tags':
                    # タグは特別処理
                    domain = child.get('domain', 'jp')
                    tags = [tag.text for tag in child.findall('tag') if tag.text]
                    video_info[f'tags_{domain}'] = tags
                elif child.text:
                    video_info[child.tag] = child.text
            
            return video_info
            
        except ET.ParseError as e:
            return {"error": f"XMLパースエラー: {str(e)}"}
    
    @staticmethod
    def _parse_ranking_rss(rss_data: str) -> List[Dict[str, Any]]:
        """ランキングRSSをパース"""
        try:
            root = ET.fromstring(rss_data)
            
            channel = root.find('.//channel')
            if channel is None:
                return []
            
            items = []
            for item in channel.findall('item'):
                video_info = {}
                
                # 基本情報を取得
                title = item.find('title')
                if title is not None and title.text:
                    video_info['title'] = title.text
                
                link = item.find('link')
                if link is not None and link.text:
                    video_info['link'] = link.text
                    # 動画IDを抽出
                    if '/watch/' in link.text:
                        video_id = link.text.split('/watch/')[-1].split('?')[0]
                        video_info['video_id'] = video_id
                
                description = item.find('description')
                if description is not None and description.text:
                    # HTMLタグを除去して統計情報を抽出
                    desc_text = description.text
                    
                    # 再生数、コメント数、マイリスト数、いいね数を抽出
                    import re
                    
                    view_match = re.search(r'再生：<strong[^>]*>([\d,]+)</strong>', desc_text)
                    if view_match:
                        video_info['view_count'] = int(view_match.group(1).replace(',', ''))
                    
                    comment_match = re.search(r'コメント：<strong[^>]*>([\d,]+)</strong>', desc_text)
                    if comment_match:
                        video_info['comment_count'] = int(comment_match.group(1).replace(',', ''))
                    
                    mylist_match = re.search(r'マイリスト：<strong[^>]*>([\d,]+)</strong>', desc_text)
                    if mylist_match:
                        video_info['mylist_count'] = int(mylist_match.group(1).replace(',', ''))
                    
                    like_match = re.search(r'いいね！：<strong[^>]*>([\d,]+)</strong>', desc_text)
                    if like_match:
                        video_info['like_count'] = int(like_match.group(1).replace(',', ''))
                    
                    # 投稿日時を抽出
                    date_match = re.search(r'(\d{4}年\d{2}月\d{2}日 \d{2}：\d{2}：\d{2})', desc_text)
                    if date_match:
                        video_info['start_time'] = date_match.group(1)
                
                if video_info:
                    items.append(video_info)
            
            return items
            
        except ET.ParseError as e:
            return []

# 既存のsearch_nicovideo関数はそのまま維持...

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

# 新規追加: 動画詳細情報取得
@mcp.tool()
def get_nicovideo_info(video_id: str) -> str:
    """
    動画IDから詳細情報を取得する（getthumbinfo API使用）
    
    Parameters:
    video_id: 動画ID（例: sm9, so123456）
    
    Returns:
    str: 動画の詳細情報
    """
    url = f"{NicovideoAPIClient.THUMBINFO_URL}{video_id}"
    xml_data = NicovideoAPIClient._make_request(url)
    
    if isinstance(xml_data, dict) and "error" in xml_data:
        return f"エラー: {xml_data['error']}"
    
    video_info = NicovideoAPIClient._parse_thumbinfo_xml(xml_data)
    
    if "error" in video_info:
        return f"エラー: {video_info['error']}"
    
    # 結果をフォーマット
    result = f"# 動画詳細情報\n\n"
    result += f"## 基本情報\n"
    
    if 'video_id' in video_info:
        result += f"- **動画ID**: {video_info['video_id']}\n"
        result += f"- **URL**: https://nico.ms/{video_info['video_id']}\n"
    
    if 'title' in video_info:
        result += f"- **タイトル**: {video_info['title']}\n"
    
    if 'description' in video_info:
        result += f"- **説明文**: {video_info['description']}\n"
    
    if 'thumbnail_url' in video_info:
        result += f"- **サムネイル**: {video_info['thumbnail_url']}\n"
    
    result += f"\n## 投稿者情報\n"
    
    if 'user_id' in video_info:
        result += f"- **ユーザーID**: {video_info['user_id']}\n"
    
    if 'user_nickname' in video_info:
        result += f"- **投稿者名**: {video_info['user_nickname']}\n"
    
    if 'ch_id' in video_info:
        result += f"- **チャンネルID**: {video_info['ch_id']}\n"
    
    if 'ch_name' in video_info:
        result += f"- **チャンネル名**: {video_info['ch_name']}\n"
    
    result += f"\n## 統計情報\n"
    
    if 'view_counter' in video_info:
        result += f"- **再生数**: {int(video_info['view_counter']):,}\n"
    
    if 'comment_num' in video_info:
        result += f"- **コメント数**: {int(video_info['comment_num']):,}\n"
    
    if 'mylist_counter' in video_info:
        result += f"- **マイリスト数**: {int(video_info['mylist_counter']):,}\n"
    
    result += f"\n## 時間情報\n"
    
    if 'first_retrieve' in video_info:
        result += f"- **投稿日時**: {video_info['first_retrieve']}\n"
    
    if 'length' in video_info:
        result += f"- **再生時間**: {video_info['length']}\n"
    
    result += f"\n## タグ\n"
    
    if 'tags_jp' in video_info:
        result += f"- **タグ（日本）**: {', '.join(video_info['tags_jp'])}\n"
    
    if 'tags_tw' in video_info and video_info['tags_tw']:
        result += f"- **タグ（台湾）**: {', '.join(video_info['tags_tw'])}\n"
    
    result += f"\n## その他\n"
    
    if 'movie_type' in video_info:
        result += f"- **動画形式**: {video_info['movie_type']}\n"
    
    if 'size_high' in video_info:
        result += f"- **ファイルサイズ**: {int(video_info['size_high']):,} bytes\n"
    
    if 'embeddable' in video_info:
        result += f"- **外部埋め込み**: {'可能' if video_info['embeddable'] == '1' else '不可'}\n"
    
    if 'no_live_play' in video_info:
        result += f"- **生放送引用**: {'不可' if video_info['no_live_play'] == '1' else '可能'}\n"
    
    return result

# 新規追加: ランキング取得
@mcp.tool()
def get_nicovideo_ranking(
    genre: str = "all",
    term: str = "24h",
    tag: Optional[str] = None,
    page: int = 1
) -> str:
    """
    ニコニコ動画のランキングを取得する
    
    Parameters:
    genre: ジャンル（all, entertainment, music_sound, dance, game等）
    term: 集計期間（hour=毎時, 24h=24時間, week=週間, month=月間, total=合計）
    tag: タグ（特定タグのランキングを取得する場合）
    page: ページ番号（1-10）
    
    Returns:
    str: ランキング情報
    """
    # ジャンルとtermの検証
    if genre not in NicovideoAPIClient.GENRES:
        return f"エラー: 無効なジャンルです。利用可能なジャンル: {', '.join(NicovideoAPIClient.GENRES)}"
    
    if term not in NicovideoAPIClient.RANKING_TERMS:
        return f"エラー: 無効な期間です。利用可能な期間: {', '.join(NicovideoAPIClient.RANKING_TERMS.keys())}"
    
    # URLを構築
    url = f"{NicovideoAPIClient.RANKING_RSS_URL}{genre}"
    params = {
        "term": term,
        "rss": "2.0",
        "lang": "ja-jp",
        "page": min(max(page, 1), 10)
    }
    
    if tag:
        params["tag"] = tag
    
    query_string = urllib.parse.urlencode(params)
    url = f"{url}?{query_string}"
    
    # リクエスト実行
    rss_data = NicovideoAPIClient._make_request(url)
    
    if isinstance(rss_data, dict) and "error" in rss_data:
        return f"エラー: {rss_data['error']}"
    
    # RSSをパース
    videos = NicovideoAPIClient._parse_ranking_rss(rss_data)
    
    if not videos:
        return "ランキング情報が取得できませんでした"
    
    # 結果をフォーマット
    result = f"# ニコニコ動画ランキング\n\n"
    result += f"- **ジャンル**: {genre}\n"
    result += f"- **期間**: {NicovideoAPIClient.RANKING_TERMS[term]}\n"
    if tag:
        result += f"- **タグ**: {tag}\n"
    result += f"- **ページ**: {page}\n"
    result += f"- **取得件数**: {len(videos)}\n\n"
    
    for i, video in enumerate(videos, 1 + (page - 1) * 100):
        result += f"## {i}位\n"
        
        if 'title' in video:
            result += f"- **タイトル**: {video['title']}\n"
        
        if 'video_id' in video:
            result += f"- **動画ID**: {video['video_id']}\n"
            result += f"- **URL**: https://nico.ms/{video['video_id']}\n"
        
        if 'view_count' in video:
            result += f"- **再生数**: {video['view_count']:,}\n"
        
        if 'comment_count' in video:
            result += f"- **コメント数**: {video['comment_count']:,}\n"
        
        if 'mylist_count' in video:
            result += f"- **マイリスト数**: {video['mylist_count']:,}\n"
        
        if 'like_count' in video:
            result += f"- **いいね数**: {video['like_count']:,}\n"
        
        if 'start_time' in video:
            result += f"- **投稿日時**: {video['start_time']}\n"
        
        result += "\n"
    
    return result

# 新規追加: ジャンル別人気動画
@mcp.tool()
def get_genre_popular_videos(
    genre: str = "all",
    term: str = "24h",
    limit: int = 10
) -> str:
    """
    特定ジャンルの人気動画を取得する（ランキングの上位を取得）
    
    Parameters:
    genre: ジャンル（all, entertainment, music_sound, dance, game等）
    term: 集計期間（hour, 24h, week, month, total）
    limit: 取得件数（最大100）
    
    Returns:
    str: ジャンル別人気動画
    """
    # limitに応じてページ数を計算（1ページ100件）
    page = 1
    actual_limit = min(limit, 100)
    
    ranking_result = get_nicovideo_ranking(genre=genre, term=term, page=page)
    
    # limitに応じて結果を切り詰める
    lines = ranking_result.split('\n')
    result_lines = []
    video_count = 0
    
    for line in lines:
        if line.startswith('## ') and '位' in line:
            video_count += 1
            if video_count > actual_limit:
                break
        result_lines.append(line)
    
    return '\n'.join(result_lines)

# 既存の関数もそのまま維持
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