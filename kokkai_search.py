import io
import json
import urllib.parse
import urllib.request
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP

# MCPサーバーを作成
mcp = FastMCP("KokkaiAPI")

class KokkaiAPIClient:
    """国会議事録検索APIクライアント"""
    
    BASE_URL = "https://kokkai.ndl.go.jp/api"
    
    # 仕様書で定義された有効な値
    VALID_HOUSES = ["衆議院", "参議院", "両院", "両院協議会"]
    VALID_SPEAKER_ROLES = ["証人", "参考人", "公述人"]
    VALID_SEARCH_RANGES = ["冒頭", "本文", "冒頭・本文"]
    
    @staticmethod
    def _validate_house_name(house_name: str) -> bool:
        """院名の妥当性チェック"""
        return house_name in KokkaiAPIClient.VALID_HOUSES
    
    @staticmethod
    def _validate_speaker_role(role: str) -> bool:
        """発言者役割の妥当性チェック"""
        return role in KokkaiAPIClient.VALID_SPEAKER_ROLES
    
    @staticmethod
    def _validate_date_format(date_str: str) -> bool:
        """日付形式のチェック（YYYY-MM-DD）"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def _validate_speech_id(speech_id: str) -> bool:
        """発言IDの形式チェック（21桁_3-4桁）"""
        pattern = r'^[A-Za-z0-9]{21}_\d{3,4}$'
        return bool(re.match(pattern, speech_id))
    
    @staticmethod
    def _validate_issue_id(issue_id: str) -> bool:
        """会議録IDの形式チェック（21桁の英数字）"""
        pattern = r'^[A-Za-z0-9]{21}$'
        return bool(re.match(pattern, issue_id))
    
    @staticmethod
    def _validate_session_number(session: int) -> bool:
        """国会回次の妥当性チェック（1-999）"""
        return 1 <= session <= 999
    
    @staticmethod
    def _validate_issue_number(issue: int) -> bool:
        """号数の妥当性チェック（0-999）"""
        return 0 <= issue <= 999
    
    @staticmethod
    def _validate_required_params(params: Dict[str, Any]) -> bool:
        """必須パラメータのチェック（制御パラメータを除外）"""
        # 制御パラメータ（検索条件ではない）
        control_params = {'recordPacking', 'maximumRecords', 'startRecord'}
        
        # 仕様書より：これらのパラメータのいずれかが必須（検索条件として）
        required_fields = [
            'nameOfHouse', 'nameOfMeeting', 'any', 'speaker', 
            'from', 'until', 'speechNumber', 'speakerPosition', 
            'speakerGroup', 'speakerRole', 'speechID', 'issueID',
            'sessionFrom', 'sessionTo', 'issueFrom', 'issueTo'
        ]
        
        # 制御パラメータを除外して検索条件のみをチェック
        search_params = {k: v for k, v in params.items() if k not in control_params}
        
        print(f"[DEBUG] Search params only: {search_params}")
        
        for field in required_fields:
            if field in search_params and search_params[field] is not None and str(search_params[field]).strip() != "":
                print(f"[DEBUG] Found required param: {field} = {search_params[field]}")
                return True
        
        print(f"[DEBUG] No required search parameters found")
        return False
    
    @staticmethod
    def _validate_params(params: Dict[str, Any], endpoint: str) -> List[str]:
        """パラメータの総合的な妥当性チェック"""
        errors = []
        
        # 必須パラメータチェック
        if not KokkaiAPIClient._validate_required_params(params):
            errors.append("検索条件として、院名、会議名、検索語、発言者名、日付、国会回次等のいずれかを指定する必要があります。")
        
        # 院名チェック
        if 'nameOfHouse' in params and params['nameOfHouse']:
            if not KokkaiAPIClient._validate_house_name(params['nameOfHouse']):
                errors.append(f"院名は {', '.join(KokkaiAPIClient.VALID_HOUSES)} のいずれかを指定してください。")
        
        # 発言者役割チェック
        if 'speakerRole' in params and params['speakerRole']:
            if not KokkaiAPIClient._validate_speaker_role(params['speakerRole']):
                errors.append(f"発言者役割は {', '.join(KokkaiAPIClient.VALID_SPEAKER_ROLES)} のいずれかを指定してください。")
        
        # 日付形式チェック
        if 'from' in params and params['from']:
            if not KokkaiAPIClient._validate_date_format(params['from']):
                errors.append("開始日付はYYYY-MM-DD形式で指定してください。")
        
        if 'until' in params and params['until']:
            if not KokkaiAPIClient._validate_date_format(params['until']):
                errors.append("終了日付はYYYY-MM-DD形式で指定してください。")
        
        # 発言IDチェック
        if 'speechID' in params and params['speechID']:
            if not KokkaiAPIClient._validate_speech_id(params['speechID']):
                errors.append("発言IDは「21桁の英数字_3-4桁の数字」の形式で指定してください。")
        
        # 会議録IDチェック
        if 'issueID' in params and params['issueID']:
            if not KokkaiAPIClient._validate_issue_id(params['issueID']):
                errors.append("会議録IDは21桁の英数字で指定してください。")
        
        # 国会回次チェック
        if 'sessionFrom' in params and params['sessionFrom'] is not None:
            if not KokkaiAPIClient._validate_session_number(params['sessionFrom']):
                errors.append("国会回次（開始）は1-999の範囲で指定してください。")
        
        if 'sessionTo' in params and params['sessionTo'] is not None:
            if not KokkaiAPIClient._validate_session_number(params['sessionTo']):
                errors.append("国会回次（終了）は1-999の範囲で指定してください。")
        
        # 号数チェック
        if 'issueFrom' in params and params['issueFrom'] is not None:
            if not KokkaiAPIClient._validate_issue_number(params['issueFrom']):
                errors.append("号数（開始）は0-999の範囲で指定してください。")
        
        if 'issueTo' in params and params['issueTo'] is not None:
            if not KokkaiAPIClient._validate_issue_number(params['issueTo']):
                errors.append("号数（終了）は0-999の範囲で指定してください。")
        
        # 発言番号チェック
        if 'speechNumber' in params and params['speechNumber'] is not None:
            if not isinstance(params['speechNumber'], int) or params['speechNumber'] < 0:
                errors.append("発言番号は0以上の整数で指定してください。")
        
        # maximumRecordsの上限チェック
        if 'maximumRecords' in params:
            if endpoint == "meeting":
                if params['maximumRecords'] > 10:
                    errors.append("会議単位出力の最大取得件数は10件です。")
            else:
                if params['maximumRecords'] > 100:
                    errors.append("最大取得件数は100件です。")
        
        # startRecordの妥当性チェック
        if 'startRecord' in params:
            if params['startRecord'] < 1:
                errors.append("開始位置は1以上で指定してください。")
        
        return errors
    
    @staticmethod
    def _build_url(endpoint: str, params: Dict[str, Any]) -> str:
        """URLを構築"""
        print(f"[DEBUG] Original params: {params}")
        
        # パラメータの妥当性チェック
        validation_errors = KokkaiAPIClient._validate_params(params, endpoint)
        if validation_errors:
            raise ValueError("パラメータエラー:\n" + "\n".join(f"- {error}" for error in validation_errors))
        
        # Noneや空文字列のパラメータを除去
        clean_params = {}
        for k, v in params.items():
            if v is not None and str(v).strip() != "":
                clean_params[k] = str(v).strip()
        
        print(f"[DEBUG] Clean params: {clean_params}")
        
        # 必須パラメータの最終確認
        required_check = KokkaiAPIClient._validate_required_params(clean_params)
        print(f"[DEBUG] Required params validation: {required_check}")
        
        # URLエンコード（UTF-8）
        query_string = urllib.parse.urlencode(clean_params, encoding='utf-8')
        print(f"[DEBUG] Query string: {query_string}")
        
        final_url = f"{KokkaiAPIClient.BASE_URL}/{endpoint}?{query_string}"
        print(f"[DEBUG] Final URL: {final_url}")
        
        return final_url
    
    @staticmethod
    def _make_request(url: str) -> Dict[str, Any]:
        """APIリクエストを実行"""
        try:
            print(f"[DEBUG] Request URL: {url}")
            
            # User-Agentを設定
            headers = {'User-Agent': 'KokkaiMCP/1.0'}
            request = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read().decode('utf-8')
                print(f"[DEBUG] Response length: {len(content)}")
                print(f"[DEBUG] Response preview: {content[:200]}")
                
                # XML応答の場合の処理
                if content.strip().startswith('<?xml'):
                    return {"error": "XML応答が返されました。recordPacking=jsonが正しく設定されていない可能性があります。"}
                
                # JSONパース
                try:
                    data = json.loads(content)
                    return data
                except json.JSONDecodeError as e:
                    return {"error": f"JSONパースエラー: {str(e)}\nレスポンス: {content[:500]}"}
                
        except urllib.error.HTTPError as e:
            try:
                error_content = e.read().decode('utf-8')
                print(f"[DEBUG] HTTP Error Content: {error_content}")
                # エラーレスポンスがJSONの場合
                if error_content.startswith('{'):
                    error_data = json.loads(error_content)
                    return {"error": f"HTTP {e.code}: {error_data}"}
                else:
                    return {"error": f"HTTP {e.code}: {error_content}"}
            except:
                return {"error": f"HTTP {e.code}: {str(e)}"}
        except urllib.error.URLError as e:
            return {"error": f"ネットワークエラー: {str(e)}"}
        except Exception as e:
            return {"error": f"予期しないエラー: {str(e)}"}
    
    @staticmethod
    def _format_results(data: Dict[str, Any], result_type: str) -> str:
        """結果をフォーマット"""
        if "error" in data:
            return f"エラー: {data['error']}"
        
        # JSON形式のエラーチェック
        if "message" in data:
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
        
        result = f"# 国会議事録検索結果\n\n"
        result += f"- 総件数: {total_records:,}\n"
        result += f"- 返戻件数: {returned_records}\n"
        result += f"- 開始位置: {start_record}\n"
        if next_position:
            result += f"- 次開始位置: {next_position}\n"
        result += "\n"
        
        if total_records == 0:
            result += "検索条件に一致する結果が見つかりませんでした。\n"
            return result
        
        if result_type == "speech":
            # 発言単位出力
            speeches = data.get("speechRecord", [])
            for i, speech in enumerate(speeches[:10], 1):  # 最大10件表示
                result += f"## 発言 {i}\n"
                result += f"- **発言者**: {speech.get('speaker', 'N/A')}\n"
                result += f"- **肩書き**: {speech.get('speakerPosition', 'N/A')}\n"
                result += f"- **所属会派**: {speech.get('speakerGroup', 'N/A')}\n"
                result += f"- **会議名**: {speech.get('nameOfMeeting', 'N/A')}\n"
                result += f"- **院名**: {speech.get('nameOfHouse', 'N/A')}\n"
                result += f"- **国会回次**: {speech.get('session', 'N/A')}\n"
                result += f"- **開催日**: {speech.get('date', 'N/A')}\n"
                result += f"- **発言番号**: {speech.get('speechOrder', 'N/A')}\n"
                
                speech_text = speech.get('speech', '')
                if speech_text:
                    # 発言内容を300文字で切り詰め
                    truncated_speech = speech_text[:300] + "..." if len(speech_text) > 300 else speech_text
                    result += f"- **発言内容**: {truncated_speech}\n"
                
                if speech.get('speechURL'):
                    result += f"- **発言URL**: {speech['speechURL']}\n"
                result += "\n"
        
        else:
            # 会議単位出力
            meetings = data.get("meetingRecord", [])
            for i, meeting in enumerate(meetings[:5], 1):  # 最大5件表示
                result += f"## 会議 {i}\n"
                result += f"- **会議名**: {meeting.get('nameOfMeeting', 'N/A')}\n"
                result += f"- **院名**: {meeting.get('nameOfHouse', 'N/A')}\n"
                result += f"- **国会回次**: {meeting.get('session', 'N/A')}\n"
                result += f"- **号数**: {meeting.get('issue', 'N/A')}\n"
                result += f"- **開催日**: {meeting.get('date', 'N/A')}\n"
                
                if meeting.get('meetingURL'):
                    result += f"- **会議録URL**: {meeting['meetingURL']}\n"
                
                # 発言レコード数
                speech_records = meeting.get('speechRecord', [])
                result += f"- **発言数**: {len(speech_records)}\n"
                result += "\n"
        
        if returned_records > 10 and result_type == "speech":
            result += f"※ 表示は最初の10件のみです。全{returned_records}件中。\n"
        elif returned_records > 5 and result_type != "speech":
            result += f"※ 表示は最初の5件のみです。全{returned_records}件中。\n"
        
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
    speakerPosition: Optional[str] = None,
    speakerGroup: Optional[str] = None,
    speakerRole: Optional[str] = None,
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
    speakerPosition: 発言者肩書き
    speakerGroup: 発言者所属会派
    speakerRole: 発言者役割（証人、参考人、公述人）
    maximumRecords: 最大取得件数（1-100、デフォルト30）
    startRecord: 開始位置（デフォルト1）
    
    Returns:
    str: 発言検索結果
    """
    # デフォルト値の設定（少なくとも1つの検索条件を確保）
    if not any and not speaker and not nameOfHouse and not nameOfMeeting and not from_date and not until_date and sessionFrom is None and sessionTo is None and not speakerPosition and not speakerGroup and not speakerRole:
        return "エラー: 検索条件を少なくとも1つ指定してください。(any, speaker, nameOfHouse, nameOfMeeting, from_date, until_date, sessionFrom, sessionTo, speakerPosition, speakerGroup, speakerRole のいずれか)"
    
    params = {
        "recordPacking": "json",
        "maximumRecords": min(max(maximumRecords, 1), 100),
        "startRecord": max(startRecord, 1)
    }
    
    print(f"[DEBUG] Input parameters - any: {any}, speaker: {speaker}, nameOfHouse: {nameOfHouse}, sessionFrom: {sessionFrom}")
    
    # 検索条件パラメータを追加
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
    if sessionFrom is not None:
        params["sessionFrom"] = sessionFrom
    if sessionTo is not None:
        params["sessionTo"] = sessionTo
    if speakerPosition:
        params["speakerPosition"] = speakerPosition
    if speakerGroup:
        params["speakerGroup"] = speakerGroup
    if speakerRole:
        params["speakerRole"] = speakerRole
    
    try:
        url = KokkaiAPIClient._build_url("speech", params)
        data = KokkaiAPIClient._make_request(url)
        return KokkaiAPIClient._format_results(data, "speech")
    except ValueError as e:
        return f"パラメータエラー: {str(e)}"

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
    国会議事録から会議を検索する
    
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
    str: 会議検索結果
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
    if sessionFrom is not None:
        params["sessionFrom"] = sessionFrom
    if sessionTo is not None:
        params["sessionTo"] = sessionTo
    
    try:
        url = KokkaiAPIClient._build_url("meeting", params)
        data = KokkaiAPIClient._make_request(url)
        return KokkaiAPIClient._format_results(data, "meeting")
    except ValueError as e:
        return f"パラメータエラー: {str(e)}"



@mcp.tool()
def get_speech_by_id(speech_id: str) -> str:
    """
    発言IDを指定して特定の発言を取得する
    
    Parameters:
    speech_id: 発言ID（会議録ID_発言番号の形式：例 100105254X00119470520_000）
    
    Returns:
    str: 発言の詳細情報
    """
    params = {
        "recordPacking": "json",
        "speechID": speech_id,
        "maximumRecords": 1
    }
    
    try:
        url = KokkaiAPIClient._build_url("speech", params)
        data = KokkaiAPIClient._make_request(url)
        return KokkaiAPIClient._format_results(data, "speech")
    except ValueError as e:
        return f"パラメータエラー: {str(e)}"

@mcp.tool()
def get_meeting_by_id(issue_id: str) -> str:
    """
    会議録IDを指定して特定の会議録を取得する
    
    Parameters:
    issue_id: 会議録ID（21桁の英数字：例 100105254X00119470520）
    
    Returns:
    str: 会議録の詳細情報
    """
    params = {
        "recordPacking": "json",
        "issueID": issue_id,
        "maximumRecords": 1
    }
    
    try:
        url = KokkaiAPIClient._build_url("meeting", params)
        data = KokkaiAPIClient._make_request(url)
        return KokkaiAPIClient._format_results(data, "meeting")
    except ValueError as e:
        return f"パラメータエラー: {str(e)}"



if __name__ == "__main__":
    # MCPサーバーを起動
    mcp.run(transport='stdio')