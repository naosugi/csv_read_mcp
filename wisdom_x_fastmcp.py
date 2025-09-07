"""
WISDOM X FastMCP Tool - 日本語質問応答システム

自然な日本語の質問文をWISDOM-Xに送信し、構文解析と質問タイプ判定は
WISDOM-X内部で実行。デフォルト100件の結果を取得。

使用: python wisdom_x_fastmcp.py
"""

import json
import urllib.parse
import urllib.request
import re
from typing import Dict, Any, List, Union
from mcp.server.fastmcp import FastMCP

# MCPサーバーを作成
mcp = FastMCP("WisdomXAPI")

class WisdomXAPIClient:
    """
    WISDOM X検索APIクライアント
    
    設計: 質問文はそのままWISDOM-Xに送信、構文解析は内部で実行、
    大量の結果を取得して情報量を確保
    """
    
    BASE_URL = "https://www.wisdom-nict.jp/webapi/qa"
    
    # 質問タイプマッピング
    QUESTION_TYPE_MAP = {
        "FactoidResultRecordBody": "what",
        "HowQAResultRecordBody": "how", 
        "WhyQAResultRecordBody": "why",
        "FAQAResultRecordBody": "what_happens",
        "DefinitionSearchResultRecordBody": "definition",
        "SuggestionRecordBody": "suggestion"
    }
    
    # 質問タイプの日本語ラベル
    QUESTION_TYPE_LABELS = {
        "what": "なに？（事実検索）",
        "how": "どうやって？（方法検索）",
        "why": "なぜ？（理由検索）",
        "what_happens": "どうなる？（因果関係検索）",
        "definition": "それなに？（定義検索）",
        "suggestion": "そもそもなにきく？（提案検索）",
        "unknown": "不明"
    }
    
    @staticmethod
    def _make_request(url: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """APIリクエストを実行"""
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "WisdomXMCP/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        except Exception as e:
            return {"error": f"APIリクエストエラー: {str(e)}"}
    
    @staticmethod
    def _detect_question_type(response_data: List[Dict]) -> str:
        """レスポンスから質問タイプを判定"""
        if not response_data or not isinstance(response_data, list):
            return "unknown"
        
        first_item = response_data[0]
        if "type" not in first_item:
            return "unknown"
        
        return WisdomXAPIClient.QUESTION_TYPE_MAP.get(first_item["type"], "unknown")
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """テキストクリーニング: ..→…、空白正規化"""
        text = re.sub(r'\.{2,}', '…', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def _clean_html_tags(text: str) -> str:
        """HTMLタグとエンティティを除去"""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return WisdomXAPIClient._clean_text(text)
    
    @staticmethod
    def _format_results(query: str, response_data: Union[List, Dict], max_results: int = 100) -> str:
        """
        検索結果をMarkdown形式でフォーマット（簡潔版）
        """
        if isinstance(response_data, dict) and "error" in response_data:
            return f"エラー: {response_data['error']}"
        
        if not response_data:
            return "検索結果が見つかりませんでした。"
        
        # 質問タイプを判定
        question_type = WisdomXAPIClient._detect_question_type(response_data)
        type_label = WisdomXAPIClient.QUESTION_TYPE_LABELS[question_type]
        
        # 結果をフォーマット
        result = f"# WISDOM X 検索結果\n"
        result += f"**クエリ**: {query}\n"
        result += f"**タイプ**: {type_label} | **総数**: {len(response_data)} | **表示**: {min(len(response_data), max_results)}\n\n"
        
        # サマリーを生成
        summary = WisdomXAPIClient._create_summary(question_type, response_data[:max_results])
        if summary:
            result += f"## サマリー\n{summary}\n\n"
        
        # 詳細結果
        result += "## 詳細\n"
        
        # 大量の結果を効率的に表示
        for i, item in enumerate(response_data[:max_results], 1):
            if "body" not in item:
                continue
            
            body = item["body"]
            
            # 10件ごとに区切りを入れる
            if i % 10 == 1 and i > 1:
                result += "---\n"
            
            result += f"\n### {i}\n"
            
            if question_type == "what":
                result += WisdomXAPIClient._format_factoid_result(body)
            elif question_type == "how":
                result += WisdomXAPIClient._format_how_result(body)
            elif question_type == "why":
                result += WisdomXAPIClient._format_why_result(body)
            elif question_type == "what_happens":
                result += WisdomXAPIClient._format_faqa_result(body)
            elif question_type == "definition":
                result += WisdomXAPIClient._format_definition_result(body)
            elif question_type == "suggestion":
                result += WisdomXAPIClient._format_suggestion_result(body)
        
        # 結果が多い場合の注記
        if len(response_data) > max_results:
            result += f"\n---\n*全{len(response_data)}件中{max_results}件表示*\n"
        
        return result
    
    @staticmethod
    def _format_factoid_result(body: Dict) -> str:
        """「なに？」タイプの結果を整形"""
        answer = WisdomXAPIClient._clean_text(body.get("answer", ""))
        context = WisdomXAPIClient._clean_text(body.get("prefix", "") + " " + body.get("suffix", ""))
        sources = body.get("sources", [])
        
        result = f"**回答**: {answer}\n"
        if context.strip():
            result += f"**文脈**: {context}\n"
        if sources and sources[0].get("url"):
            result += f"**URL**: {sources[0]['url']}\n"
        
        return result
    
    @staticmethod
    def _format_how_result(body: Dict) -> str:
        """「どうやって？」タイプの結果を整形"""
        answer = WisdomXAPIClient._clean_html_tags(body.get("answer", ""))
        sources = body.get("sources", [])
        
        if answer and len(answer) > 300:
            result = f"**方法**: {answer[:300]}...\n"
        else:
            result = f"**方法**: {answer}\n"
        if sources and sources[0].get("url"):
            result += f"**URL**: {sources[0]['url']}\n"
        
        return result
    
    @staticmethod
    def _format_why_result(body: Dict) -> str:
        """「なぜ？」タイプの結果を整形"""
        answer = WisdomXAPIClient._clean_html_tags(body.get("answer", ""))
        sources = body.get("sources", [])
        
        # 重要文を抽出
        important_match = re.search(r'<strong>(.*?)</strong>', body.get("answer", ""))
        important = WisdomXAPIClient._clean_html_tags(important_match.group(1)) if important_match else ""
        
        if answer and len(answer) > 200:
            result = f"**理由**: {answer[:200]}...\n"
        else:
            result = f"**理由**: {answer}\n"
        
        if important and important != answer:
            result += f"**重要**: {important}\n"
        
        if sources and sources[0].get("url"):
            result += f"**URL**: {sources[0]['url']}\n"
        
        return result
    
    @staticmethod
    def _format_faqa_result(body: Dict) -> str:
        """「どうなる？」タイプの結果を整形"""
        children = body.get("children", [])
        if not children:
            return ""
        
        result = "**因果**:\n"
        for j, child in enumerate(children[:3], 1):
            cause = child.get("cause_sentence_endform", "")
            effect = child.get("effect_sentence_endform", "")
            url = child.get("url", "")
            
            if cause and effect:
                result += f"{j}. {cause} → {effect}"
                if url:
                    result += f" [{url}]"
                result += "\n"
        
        return result
    
    @staticmethod
    def _format_definition_result(body: Dict) -> str:
        """「それなに？」タイプの結果を整形"""
        result = ""
        if body.get("key"):
            result += f"**用語**: {body['key']}\n"
        if body.get("sentence"):
            result += f"**定義**: {body['sentence']}\n"
        if body.get("url"):
            result += f"**URL**: {body['url']}\n"
        return result
    
    @staticmethod
    def _format_suggestion_result(body: Dict) -> str:
        """「そもそもなにきく？」タイプの結果を整形"""
        result = ""
        if body.get("question"):
            result += f"**提案**: {body['question']}\n"
        if body.get("category"):
            result += f"**種別**: {body['category']}\n"
        return result
    
    @staticmethod
    def _create_summary(question_type: str, results: List[Dict]) -> str:
        """検索結果のサマリーを生成（簡潔版）"""
        if not results:
            return ""
        
        if question_type == "what":
            answers = []
            for r in results[:10]:
                if "body" in r and r["body"].get("answer"):
                    answer = r["body"]["answer"]
                    if answer not in answers:
                        answers.append(answer)
            return f"主な回答: {', '.join(answers[:7])}" if answers else ""
        
        elif question_type == "how":
            return f"{len(results)}件の方法が見つかりました"
        
        elif question_type == "why":
            reasons = []
            for r in results[:5]:
                if "body" in r:
                    body = r["body"]
                    match = re.search(r'<strong>(.*?)</strong>', body.get("answer", ""))
                    if match:
                        reason = WisdomXAPIClient._clean_html_tags(match.group(1))
                        if reason and len(reason) < 100 and reason not in reasons:
                            reasons.append(reason)
            return f"主な理由: {'; '.join(reasons[:3])}" if reasons else "複数の理由あり"
        
        elif question_type == "what_happens":
            effects = []
            for r in results[:5]:
                if "body" in r and r["body"].get("children"):
                    for child in r["body"]["children"][:2]:
                        effect = child.get("effect_sentence_endform", "")
                        if effect and effect not in effects:
                            effects.append(effect)
            return f"主な結果: {' → '.join(effects[:5])}" if effects else ""
        
        elif question_type == "definition":
            defs = []
            for r in results[:2]:
                if "body" in r:
                    term = r["body"].get("key", "")
                    definition = r["body"].get("sentence", "")
                    if term and definition:
                        defs.append(f"{term}: {definition[:80]}...")
            return "\n".join(defs) if defs else ""
        
        elif question_type == "suggestion":
            questions = []
            for r in results[:10]:
                if "body" in r and r["body"].get("question"):
                    q = r["body"]["question"]
                    if q not in questions:
                        questions.append(q)
            return f"関連質問: {', '.join(questions[:5])}" if questions else ""
        
        return ""

# メインの検索関数（1つのみ）
@mcp.tool()
def search_wisdom_x(
    query: str,
    max_results: int = 100
) -> str:
    """
    WISDOM Xで日本語の質問を検索する
    
    **重要**: ユーザーの自然な質問文をそのまま送信すること。
    キーワード抽出やスペース区切りは厳禁。
    
    Parameters:
    -----------
    query : str
        自然な日本語の質問文をそのまま使用
        正: "AIはどんな社会問題の解決に使える？"
        誤: "AI 社会問題 解決" ❌
    
    max_results : int, optional
        最大結果数（デフォルト100、推奨100以上）
    
    Returns:
    --------
    str
        Markdown形式の結果（質問タイプ、サマリー、詳細を含む）
        質問タイプはWISDOM-Xが自動判定
    
    Example:
    --------
    >>> user_input = "なぜ日本は少子高齢化が進んでいるのですか？"
    >>> result = search_wisdom_x(user_input)  # そのまま送信
    
    Note:
    -----
    WISDOM-Xは質問応答システム。構文解析は内部で実行。
    """
    # パラメータの検証
    max_results = max(max_results, 1)
    
    # URLエンコード
    encoded_query = urllib.parse.quote(query)
    url = f"{WisdomXAPIClient.BASE_URL}/{encoded_query}/any"
    
    # リクエスト実行
    response_data = WisdomXAPIClient._make_request(url)
    
    # 結果をフォーマット
    return WisdomXAPIClient._format_results(query, response_data, max_results)

if __name__ == "__main__":
    """MCPサーバー起動（stdio）"""
    mcp.run(transport='stdio')