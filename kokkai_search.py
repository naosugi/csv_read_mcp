import io
import json
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP

# MCPサーバーを作成
mcp = FastMCP("KokkaiAPI")

class KokkaiAPIClient:
    """国会議事録検索APIクライアント"""
    
    BASE_URL = "https://kokkai.ndl.go.jp/api"
    
    @staticmethod
    def _build_url(endpoint: str, params: Dict[str, Any]) -> str:
        """URLを構築"""
        # Noneや空文字列のパラメータを除去
        clean_params = {k: v for k, v in params.items() if v is not None and v != ""}
        
        # URLエンコード
        query_string = urllib.parse.urlencode(clean_params, encoding='utf-8')
        
        return f"{KokkaiAPIClient.BASE_URL}/{endpoint}?{query_string}"
    
    @staticmethod
    def _make_request(url: str) -> Dict[str, Any]:
        """APIリクエストを実行"""
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            return {"error": f"APIリクエストエラー: {str(e)}"}
    
    @staticmethod
    def _format_results(data: Dict[str, Any], result_type: str) -> str:
        """結果をフォーマット"""
        if "error" in data:
            return f"エラー: {data['error']}"
        
        if "message" in data:
            # エラーレスポンス
            details = data.get("details", [])
            error_msg = f"APIエラー: {data['message']}"
            if details:
                error_msg += f"\n詳細: {', '.join(details)}"
            return error_msg
        
        # 正常レスポンス
        total_records = data.get("numberOfRecords", 0)
        returned_records = data.get("numberOfReturn", 0)
        start_record = data.get("startRecord", 1)
        next_position = data.get("nextRecordPosition")
        
        result = f"# 検索結果\n\n"
        result += f"- 総件数: {total_records}\n"
        result += f"- 返戻件数: {returned_records}\n"
        result += f"- 開始位置: {start_record}\n"
        if next_position:
            result += f"- 次開始位置: {next_position}\n"
        result += "\n"
        
        if result_type == "speech":
            # 発言単位出力
            speeches = data.get("speechRecord", [])
            for i, speech in enumerate(speeches[:5], 1):  # 最大5件表示
                result += f"## 発言 {i}\n"
                result += f"- 発言者: {speech.get('speaker', 'N/A')}\n"
                result += f"- 肩書き: {speech.get('speakerPosition', 'N/A')}\n"
                result += f"- 所属会派: {speech.get('speakerGroup', 'N/A')}\n"
                result += f"- 会議名: {speech.get('nameOfMeeting', 'N/A')}\n"
                result += f"- 院名: {speech.get('nameOfHouse', 'N/A')}\n"
                result += f"- 国会回次: {speech.get('session', 'N/A')}\n"
                result += f"- 開催日: {speech.get('date', 'N/A')}\n"
                
                speech_text = speech.get('speech', '')
                if speech_text:
                    # 発言内容を200文字で切り詰め
                    truncated_speech = speech_text[:200] + "..." if len(speech_text) > 200 else speech_text
                    result += f"- 発言内容: {truncated_speech}\n"
                
                if speech.get('speechURL'):
                    result += f"- 発言URL: {speech['speechURL']}\n"
                result += "\n"
        
        else:
            # 会議単位出力
            meetings = data.get("meetingRecord", [])
            for i, meeting in enumerate(meetings[:3], 1):  # 最大3件表示
                result += f"## 会議 {i}\n"
                result += f"- 会議名: {meeting.get('nameOfMeeting', 'N/A')}\n"
                result += f"- 院名: {meeting.get('nameOfHouse', 'N/A')}\n"
                result += f"- 国会回次: {meeting.get('session', 'N/A')}\n"
                result += f"- 号数: {meeting.get('issue', 'N/A')}\n"
                result += f"- 開催日: {meeting.get('date', 'N/A')}\n"
                
                if meeting.get('meetingURL'):
                    result += f"- 会議録URL: {meeting['meetingURL']}\n"
                
                # 発言レコード数
                speech_records = meeting.get('speechRecord', [])
                result += f"- 発言数: {len(speech_records)}\n"
                result += "\n"
        
        if returned_records > 5 and result_type == "speech":
            result += f"※ 表示は最初の5件のみです。全{returned_records}件中。\n"
        elif returned_records > 3 and result_type != "speech":
            result += f"※ 表示は最初の3件のみです。全{returned_records}件中。\n"
        
        return result

@mcp.tool()
def search_kokkai_speeches(
    any: Optional[str] = None,
    speaker: Optional[str] = None,
    nameOfHouse: Optional[str] = None,
    nameOfMeeting: Optional[str] = None,
    from_date: Optional[str] = None,
    until_date: Optional[str] = None,
    sessionFrom: Optional[int] = None,
    sessionTo: Optional[int] = None,
    maximumRecords: int = 30,
    startRecord: int = 1
) -> str:
    """
    国会議事録から発言を検索する
    
    Parameters:
    any: 検索語（発言内容に含まれる言葉）
    speaker: 発言者名（議員名等）
    nameOfHouse: 院名（衆議院、参議院、両院、両院協議会）
    nameOfMeeting: 会議名（本会議、委員会等）
    from_date: 開会日付の始点（YYYY-MM-DD形式）
    until_date: 開会日付の終点（YYYY-MM-DD形式）
    sessionFrom: 国会回次の開始
    sessionTo: 国会回次の終了
    maximumRecords: 最大取得件数（1-100、デフォルト30）
    startRecord: 開始位置（デフォルト1）
    
    Returns:
    str: 発言検索結果
    """
    params = {
        "recordPacking": "json",
        "maximumRecords": min(max(maximumRecords, 1), 100),
        "startRecord": max(startRecord, 1)
    }
    
    if any:
        params["any"] = any
    if speaker:
        params["speaker"] = speaker
    if nameOfHouse:
        params["nameOfHouse"] = nameOfHouse
    if nameOfMeeting:
        params["nameOfMeeting"] = nameOfMeeting
    if from_date:
        params["from"] = from_date
    if until_date:
        params["until"] = until_date
    if sessionFrom:
        params["sessionFrom"] = sessionFrom
    if sessionTo:
        params["sessionTo"] = sessionTo
    
    url = KokkaiAPIClient._build_url("speech", params)
    data = KokkaiAPIClient._make_request(url)
    
    return KokkaiAPIClient._format_results(data, "speech")

@mcp.tool()
def search_kokkai_meetings(
    any: Optional[str] = None,
    nameOfHouse: Optional[str] = None,
    nameOfMeeting: Optional[str] = None,
    from_date: Optional[str] = None,
    until_date: Optional[str] = None,
    sessionFrom: Optional[int] = None,
    sessionTo: Optional[int] = None,
    maximumRecords: int = 3,
    startRecord: int = 1
) -> str:
    """
    国会議事録から会議を検索する（詳細情報付き）
    
    Parameters:
    any: 検索語（発言内容に含まれる言葉）
    nameOfHouse: 院名（衆議院、参議院、両院、両院協議会）
    nameOfMeeting: 会議名（本会議、委員会等）
    from_date: 開会日付の始点（YYYY-MM-DD形式）
    until_date: 開会日付の終点（YYYY-MM-DD形式）
    sessionFrom: 国会回次の開始
    sessionTo: 国会回次の終了
    maximumRecords: 最大取得件数（1-10、デフォルト3）
    startRecord: 開始位置（デフォルト1）
    
    Returns:
    str: 会議検索結果（詳細）
    """
    params = {
        "recordPacking": "json",
        "maximumRecords": min(max(maximumRecords, 1), 10),
        "startRecord": max(startRecord, 1)
    }
    
    if any:
        params["any"] = any
    if nameOfHouse:
        params["nameOfHouse"] = nameOfHouse
    if nameOfMeeting:
        params["nameOfMeeting"] = nameOfMeeting
    if from_date:
        params["from"] = from_date
    if until_date:
        params["until"] = until_date
    if sessionFrom:
        params["sessionFrom"] = sessionFrom
    if sessionTo:
        params["sessionTo"] = sessionTo
    
    url = KokkaiAPIClient._build_url("meeting", params)
    data = KokkaiAPIClient._make_request(url)
    
    return KokkaiAPIClient._format_results(data, "meeting")

@mcp.tool()
def search_kokkai_meetings_simple(
    any: Optional[str] = None,
    nameOfHouse: Optional[str] = None,
    nameOfMeeting: Optional[str] = None,
    from_date: Optional[str] = None,
    until_date: Optional[str] = None,
    sessionFrom: Optional[int] = None,
    sessionTo: Optional[int] = None,
    maximumRecords: int = 30,
    startRecord: int = 1
) -> str:
    """
    国会議事録から会議を検索する（簡易版）
    
    Parameters:
    any: 検索語（発言内容に含まれる言葉）
    nameOfHouse: 院名（衆議院、参議院、両院、両院協議会）
    nameOfMeeting: 会議名（本会議、委員会等）
    from_date: 開会日付の始点（YYYY-MM-DD形式）
    until_date: 開会日付の終点（YYYY-MM-DD形式）
    sessionFrom: 国会回次の開始
    sessionTo: 国会回次の終了
    maximumRecords: 最大取得件数（1-100、デフォルト30）
    startRecord: 開始位置（デフォルト1）
    
    Returns:
    str: 会議検索結果（簡易）
    """
    params = {
        "recordPacking": "json",
        "maximumRecords": min(max(maximumRecords, 1), 100),
        "startRecord": max(startRecord, 1)
    }
    
    if any:
        params["any"] = any
    if nameOfHouse:
        params["nameOfHouse"] = nameOfHouse
    if nameOfMeeting:
        params["nameOfMeeting"] = nameOfMeeting
    if from_date:
        params["from"] = from_date
    if until_date:
        params["until"] = until_date
    if sessionFrom:
        params["sessionFrom"] = sessionFrom
    if sessionTo:
        params["sessionTo"] = sessionTo
    
    url = KokkaiAPIClient._build_url("meeting_list", params)
    data = KokkaiAPIClient._make_request(url)
    
    return KokkaiAPIClient._format_results(data, "meeting_simple")

@mcp.tool()
def get_speech_by_id(speech_id: str) -> str:
    """
    発言IDを指定して特定の発言を取得する
    
    Parameters:
    speech_id: 発言ID（会議録ID_発言番号の形式）
    
    Returns:
    str: 発言の詳細情報
    """
    params = {
        "recordPacking": "json",
        "speechID": speech_id,
        "maximumRecords": 1
    }
    
    url = KokkaiAPIClient._build_url("speech", params)
    data = KokkaiAPIClient._make_request(url)
    
    return KokkaiAPIClient._format_results(data, "speech")

@mcp.tool()
def get_meeting_by_id(issue_id: str) -> str:
    """
    会議録IDを指定して特定の会議録を取得する
    
    Parameters:
    issue_id: 会議録ID（21桁の英数字）
    
    Returns:
    str: 会議録の詳細情報
    """
    params = {
        "recordPacking": "json",
        "issueID": issue_id,
        "maximumRecords": 1
    }
    
    url = KokkaiAPIClient._build_url("meeting", params)
    data = KokkaiAPIClient._make_request(url)
    
    return KokkaiAPIClient._format_results(data, "meeting")

@mcp.tool()
def search_recent_kokkai_speeches(
    any: str,
    days_back: int = 365,
    nameOfHouse: Optional[str] = None,
    maximumRecords: int = 10
) -> str:
    """
    最近の国会発言を検索する（便利関数）
    
    Parameters:
    any: 検索語（必須）
    days_back: 何日前まで遡るか（デフォルト365日）
    nameOfHouse: 院名（衆議院、参議院、両院、両院協議会）
    maximumRecords: 最大取得件数（1-100、デフォルト10）
    
    Returns:
    str: 発言検索結果
    """
    from datetime import datetime, timedelta
    
    # 現在日時から指定日数前の日付を計算
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    from_date = start_date.strftime("%Y-%m-%d")
    until_date = end_date.strftime("%Y-%m-%d")
    
    return search_kokkai_speeches(
        any=any,
        nameOfHouse=nameOfHouse,
        from_date=from_date,
        until_date=until_date,
        maximumRecords=maximumRecords
    )

if __name__ == "__main__":
    # MCPサーバーを起動
    mcp.run(transport='stdio')