import json
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any, List, Union, Tuple
from mcp.server.fastmcp import FastMCP
import re

# MCPサーバーを作成
mcp = FastMCP("LawsAI", description="""
法令検索API v2のAI連携用MCPツール

このツールセットは日本の法令を検索・取得するための純粋な機能を提供します。
効果的な使用のため、最初に get_search_guidance() を呼び出してガイダンスを確認してください。

主な機能：
- キーワード検索（search_laws_by_keyword）
- 法令名検索（search_laws_by_title）
- 法令本文取得（get_law_content）
- 検索結果分析（analyze_search_results）
- 検索戦略提案（get_search_suggestions）
""")

# 段階的検索ガイダンス
SEARCH_GUIDANCE = """
# 法令検索AI向けガイダンス

## 効果的な法令検索の段階的アプローチ

### 1. 初期検索戦略
自然言語クエリから法的概念を抽出し、以下の順序で検索を試みてください：
1. 主要な名詞でキーワード検索（例：「シートベルト」「着用」）
2. 法令用語への変換を試行（例：「シートベルト」→「座席ベルト」）
3. 関連する法令名での検索（例：交通関連→「道路交通法」）

### 2. 検索結果の評価
- 複数の法令がヒットした場合、カテゴリーと内容から最も関連性の高いものを特定
- 条文中に定義されていない用語（例：「幼児」）が出現した場合、その定義を別途検索
- 検索結果が0件の場合、キーワードを減らすか、類義語で再検索

### 3. 深掘り検索
- 該当法令が特定できたら、より詳細な条文を取得
- 参照されている他の法令（例：「児童福祉法に定める」）があれば、その法令も検索
- 年齢や数値に関する規定は、前後の条文も確認

### 4. 回答生成時の注意
- 法令間の参照関係は明示的に述べる（例：「道路交通法では『幼児』の定義は明記されていないが、一般に児童福祉法の定義（6歳未満）が適用されると考えられる」）
- 検索で確認できなかった事項は推論であることを明示
- 複数の解釈が可能な場合は、その旨を記載

### 5. 具体例：年齢に関する規定の検索
質問：「X歳でYは可能か？」
1. Yに関する法令をキーワード検索
2. 年齢制限や年齢区分（幼児、児童、未成年等）を含む条文を特定
3. 年齢区分の定義を他の法令で検索
4. 該当年齢がどの区分に該当するか判断

### 6. よく使われる年齢区分の検索ヒント
法令でよく使われる年齢区分を検索する際のキーワード：
- 「幼児」→ 「児童福祉法」で定義を検索
- 「児童」→ 「児童福祉法」「学校教育法」で定義を検索
- 「未成年」→ 「民法」で定義を検索
- 「少年」→ 「少年法」で定義を検索

### 7. 表記揺れへの対処
同じ概念でも法令により表記が異なる場合があります：
- 「シートベルト」「座席ベルト」
- 「自動車」「車両」「車」
- 「道路」「道」
複数の表記で検索を試みてください。

このガイダンスに従って、段階的かつ体系的な検索を実行してください。
"""

class LawsAPIClient:
    """法令API v2 クライアント（純粋なAPI呼び出しのみ）"""
    
    BASE_URL = "https://laws.e-gov.go.jp/api/2"
    
    @staticmethod
    def _make_request(url: str) -> Dict[str, Any]:
        """APIリクエストを実行"""
        try:
            headers = {
                'User-Agent': 'LawsAIMCP/1.0',
                'Accept': 'application/json'
            }
            request = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read().decode('utf-8')
                return json.loads(content)
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                error_content = e.read().decode('utf-8')
                error_data = json.loads(error_content)
                if error_data.get("code") == "404001":
                    return {"results": [], "total_count": 0, "error": "no_results"}
                return {"error": f"http_error_{e.code}", "message": error_data.get("message", "")}
            raise
        except Exception as e:
            return {"error": "request_failed", "message": str(e)}
    
    @staticmethod
    def call_api(endpoint: str, params: Dict[str, Any], path_param: Optional[str] = None) -> Dict[str, Any]:
        """汎用APIコール"""
        # パラメータをクエリ文字列に変換
        clean_params = {}
        for k, v in params.items():
            if v is not None:
                if isinstance(v, list):
                    clean_params[k] = ','.join(str(item) for item in v)
                else:
                    clean_params[k] = str(v)
        
        query_string = urllib.parse.urlencode(clean_params, encoding='utf-8')
        
        # URL構築
        if path_param:
            url = f"{LawsAPIClient.BASE_URL}/{endpoint}/{urllib.parse.quote(path_param, safe='')}"
        else:
            url = f"{LawsAPIClient.BASE_URL}/{endpoint}"
        
        if query_string:
            url += f"?{query_string}"
        
        return LawsAPIClient._make_request(url)

class ResponseFormatter:
    """レスポンスの構造化と整形"""
    
    @staticmethod
    def format_search_results(results: Dict[str, Any], search_type: str) -> Dict[str, Any]:
        """検索結果を構造化された形式で返す"""
        formatted = {
            "search_type": search_type,
            "total_count": 0,
            "returned_count": 0,
            "has_error": False,
            "error_message": "",
            "items": [],
            "search_hints": {}
        }
        
        if "error" in results:
            formatted["has_error"] = True
            formatted["error_message"] = results.get("message", results.get("error", ""))
            return formatted
        
        # 検索タイプに応じた処理
        if search_type == "keyword":
            formatted["total_count"] = results.get("total_count", 0)
            formatted["returned_count"] = results.get("sentence_count", 0)
            
            items = results.get("items", [])
            for item in items:
                law_info = item.get("law_info", {})
                revision_info = item.get("revision_info", {})
                sentences = item.get("sentences", [])
                
                for sentence in sentences:
                    formatted["items"].append({
                        "law_id": law_info.get("law_id"),
                        "law_title": revision_info.get("law_title"),
                        "law_num": law_info.get("law_num"),
                        "position": sentence.get("position"),
                        "text": re.sub(r'<[^>]+>', '', sentence.get("text", "")),
                        "raw_text": sentence.get("text", "")
                    })
            
            # 検索ヒントの生成
            if formatted["total_count"] > formatted["returned_count"]:
                formatted["search_hints"]["has_more"] = True
                formatted["search_hints"]["next_offset"] = results.get("next_offset", 0)
            
        elif search_type == "laws":
            formatted["total_count"] = results.get("total_count", 0)
            formatted["returned_count"] = results.get("count", 0)
            
            laws = results.get("laws", [])
            for law in laws:
                law_info = law.get("law_info", {})
                revision_info = law.get("revision_info", {})
                
                formatted["items"].append({
                    "law_id": law_info.get("law_id"),
                    "law_title": revision_info.get("law_title"),
                    "law_num": law_info.get("law_num"),
                    "law_type": law_info.get("law_type"),
                    "promulgation_date": law_info.get("promulgation_date"),
                    "last_amendment_date": revision_info.get("amendment_promulgate_date"),
                    "category": revision_info.get("category")
                })
        
        elif search_type == "law_data":
            law_info = results.get("law_info", {})
            revision_info = results.get("revision_info", {})
            
            formatted["total_count"] = 1
            formatted["returned_count"] = 1
            formatted["items"] = [{
                "law_id": law_info.get("law_id"),
                "law_title": revision_info.get("law_title"),
                "law_num": law_info.get("law_num"),
                "law_full_text": results.get("law_full_text", {}),
                "has_attachments": bool(results.get("attached_files_info"))
            }]
        
        return formatted
    
    @staticmethod
    def extract_articles_from_law_data(law_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """法令データから条文を抽出"""
        articles = []
        
        def parse_element(element: Any, context: Dict[str, Any] = None) -> None:
            if not isinstance(element, dict):
                return
            
            tag = element.get("tag", "")
            
            if tag == "Article":
                article_num = element.get("attr", {}).get("Num", "")
                article_text = ResponseFormatter._extract_text(element)
                
                if article_num and article_text:
                    articles.append({
                        "article_num": article_num,
                        "article_text": article_text,
                        "char_count": len(article_text)
                    })
            
            # 子要素の処理
            children = element.get("children", [])
            if isinstance(children, list):
                for child in children:
                    parse_element(child, context)
        
        law_full_text = law_data.get("law_full_text", {})
        parse_element(law_full_text)
        
        return articles
    
    @staticmethod
    def _extract_text(element: Any) -> str:
        """要素からテキストを再帰的に抽出"""
        if isinstance(element, str):
            return element
        elif isinstance(element, dict):
            text_parts = []
            children = element.get("children", [])
            if isinstance(children, list):
                for child in children:
                    text_parts.append(ResponseFormatter._extract_text(child))
            return "".join(text_parts)
        return ""

@mcp.tool()
def search_laws_by_keyword(
    keywords: List[str],
    limit: int = 10,
    offset: int = 0,
    law_type: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> str:
    """
    キーワードで法令本文を検索
    
    Parameters:
    keywords: 検索キーワードのリスト（スペース区切りでAND検索）
    limit: 取得件数上限（デフォルト: 10）
    offset: 取得開始位置（ページング用）
    law_type: 法令種別フィルタ（Act, CabinetOrder等）
    date_from: 公布日開始（YYYY-MM-DD）
    date_to: 公布日終了（YYYY-MM-DD）
    
    Returns:
    str: 構造化された検索結果（JSON形式）
    
    検索結果には以下が含まれます：
    - total_count: 該当件数
    - items: 検索結果（法令情報と該当箇所）
    - search_hints: 次の検索のためのヒント
    
    **ヒント**: 初めて検索する場合は、先に get_search_guidance() を呼び出して
    効果的な検索戦略を確認することをお勧めします。
    """
    try:
        params = {
            "keyword": " ".join(keywords),
            "limit": limit,
            "offset": offset,
            "sentence_text_size": 300
        }
        
        if law_type:
            params["law_type"] = law_type
        if date_from:
            params["promulgation_date_from"] = date_from
        if date_to:
            params["promulgation_date_to"] = date_to
        
        results = LawsAPIClient.call_api("keyword", params)
        formatted = ResponseFormatter.format_search_results(results, "keyword")
        
        # 追加の検索ヒント
        if formatted["total_count"] == 0:
            formatted["search_hints"]["suggestions"] = [
                "キーワードを減らして検索",
                "類義語や関連語で検索",
                "法令名で直接検索"
            ]
        
        return json.dumps(formatted, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": "search_failed",
            "message": str(e)
        }, ensure_ascii=False)

@mcp.tool()
def search_laws_by_title(
    title_keywords: List[str],
    limit: int = 10,
    law_type: Optional[List[str]] = None,
    include_repealed: bool = False
) -> str:
    """
    法令名で法令を検索
    
    Parameters:
    title_keywords: 法令名に含まれるキーワードのリスト
    limit: 取得件数上限
    law_type: 法令種別フィルタ
    include_repealed: 廃止法令を含むか
    
    Returns:
    str: 法令一覧（JSON形式）
    """
    try:
        params = {
            "law_title": " ".join(title_keywords),
            "limit": limit
        }
        
        if law_type:
            params["law_type"] = law_type
        
        if not include_repealed:
            params["repeal_status"] = ["None"]
        
        results = LawsAPIClient.call_api("laws", params)
        formatted = ResponseFormatter.format_search_results(results, "laws")
        
        return json.dumps(formatted, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": "search_failed",
            "message": str(e)
        }, ensure_ascii=False)

@mcp.tool()
def get_law_content(
    law_id: str,
    extract_articles: bool = True,
    target_date: Optional[str] = None
) -> str:
    """
    法令IDから法令本文を取得
    
    Parameters:
    law_id: 法令ID
    extract_articles: 条文を抽出して構造化するか
    target_date: 時点指定（YYYY-MM-DD）
    
    Returns:
    str: 法令本文または構造化された条文（JSON形式）
    """
    try:
        params = {
            "law_full_text_format": "json"
        }
        
        if target_date:
            params["asof"] = target_date
        
        results = LawsAPIClient.call_api("law_data", params, law_id)
        
        if "error" in results:
            return json.dumps(results, ensure_ascii=False)
        
        # 基本情報
        law_info = results.get("law_info", {})
        revision_info = results.get("revision_info", {})
        
        output = {
            "law_id": law_info.get("law_id"),
            "law_title": revision_info.get("law_title"),
            "law_num": law_info.get("law_num"),
            "promulgation_date": law_info.get("promulgation_date"),
            "last_amendment": revision_info.get("amendment_promulgate_date")
        }
        
        if extract_articles:
            # 条文を抽出
            articles = ResponseFormatter.extract_articles_from_law_data(results)
            output["articles"] = articles
            output["article_count"] = len(articles)
        else:
            # 生データを含める
            output["law_full_text"] = results.get("law_full_text", {})
        
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": "get_law_failed",
            "message": str(e)
        }, ensure_ascii=False)

@mcp.tool()
def get_search_guidance() -> str:
    """
    法令検索のベストプラクティスとガイダンスを取得
    
    Returns:
    str: 段階的検索アプローチのガイダンス
    
    **重要**: 法令検索を開始する前に、このツールを呼び出してガイダンスを確認することを強く推奨します。
    効果的な検索戦略と注意事項が含まれています。
    """
    return SEARCH_GUIDANCE
    """
    検索クエリに対する検索戦略の提案
    
    Parameters:
    query: 元の検索クエリ
    context: 前回の検索結果などのコンテキスト情報
    
    Returns:
    str: 検索戦略の提案（JSON形式）
    
    このツールは以下を提供します：
    - 推奨キーワード
    - 検索の順序
    - フィルタリング条件
    - 代替検索方法
    """
    try:
        suggestions = {
            "original_query": query,
            "search_strategies": []
        }
        
        # 基本的な検索戦略
        # 1. 名詞を抽出して検索
        nouns = re.findall(r'[一-龥ぁ-んァ-ヶー]+', query)
        if nouns:
            suggestions["search_strategies"].append({
                "strategy": "keyword_search",
                "description": "重要な名詞でキーワード検索",
                "keywords": nouns,
                "reason": "自然言語クエリから重要な概念を抽出"
            })
        
        # 2. 法令名の可能性を探る
        law_indicators = ["法", "令", "規則", "条例", "規程"]
        for indicator in law_indicators:
            if indicator in query:
                suggestions["search_strategies"].append({
                    "strategy": "law_title_search",
                    "description": "法令名で直接検索",
                    "keywords": [word for word in nouns if len(word) > 2],
                    "reason": f"クエリに「{indicator}」が含まれている"
                })
                break
        
        # 3. 年齢・数値が含まれる場合
        numbers = re.findall(r'\d+', query)
        if numbers:
            suggestions["search_strategies"].append({
                "strategy": "related_search",
                "description": "数値に関連する規定を検索",
                "keywords": nouns + [f"{num}歳" for num in numbers],
                "reason": "年齢や数値に関する規定の可能性"
            })
        
        # 4. コンテキストに基づく提案
        if context and context.get("previous_search_type") == "keyword":
            if context.get("total_count", 0) == 0:
                suggestions["search_strategies"].append({
                    "strategy": "broader_search",
                    "description": "より広いキーワードで再検索",
                    "keywords": nouns[:2] if len(nouns) > 2 else nouns,
                    "reason": "前回の検索で結果が得られなかった"
                })
            elif context.get("total_count", 0) > 50:
                suggestions["search_strategies"].append({
                    "strategy": "narrow_search",
                    "description": "追加キーワードで絞り込み",
                    "keywords": nouns + ["義務", "規定", "条件"],
                    "reason": "検索結果が多すぎる"
                })
        
        # 5. 一般的な法令カテゴリの提案
        category_keywords = {
            "交通": ["道路交通法", "道路運送車両法"],
            "労働": ["労働基準法", "労働安全衛生法"],
            "教育": ["学校教育法", "教育基本法"],
            "医療": ["医療法", "医師法"],
            "税": ["所得税法", "法人税法", "消費税法"]
        }
        
        for category, laws in category_keywords.items():
            if category in query:
                suggestions["search_strategies"].append({
                    "strategy": "category_search",
                    "description": f"{category}関連の主要法令を検索",
                    "target_laws": laws,
                    "reason": f"「{category}」に関する質問の可能性"
                })
        
        return json.dumps(suggestions, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": "suggestion_failed",
            "message": str(e)
        }, ensure_ascii=False)

@mcp.tool()
def analyze_search_results(
    search_results: List[Dict[str, Any]],
    original_query: str
) -> str:
    """
    検索結果を分析し、関連性や次のアクションを提案
    
    Parameters:
    search_results: 検索結果のリスト
    original_query: 元の検索クエリ
    
    Returns:
    str: 分析結果と提案（JSON形式）
    """
    try:
        analysis = {
            "original_query": original_query,
            "total_results": len(search_results),
            "law_distribution": {},
            "relevance_indicators": [],
            "undefined_terms": [],
            "referenced_laws": [],
            "suggested_actions": []
        }
        
        # 法令ごとの分布を分析
        law_count = {}
        for result in search_results:
            law_id = result.get("law_id", "unknown")
            law_title = result.get("law_title", "不明")
            if law_id not in law_count:
                law_count[law_id] = {
                    "title": law_title,
                    "count": 0,
                    "positions": []
                }
            law_count[law_id]["count"] += 1
            law_count[law_id]["positions"].append(result.get("position", ""))
        
        analysis["law_distribution"] = law_count
        
        # 関連性の指標を計算
        query_words = set(re.findall(r'[一-龥ぁ-んァ-ヶー]+', original_query.lower()))
        
        # 未定義用語と参照法令を検出
        age_terms = ["幼児", "児童", "未成年", "少年", "成年"]
        law_references = []
        
        for result in search_results[:10]:  # 上位10件を詳細分析
            text = result.get("text", "").lower()
            
            # キーワードマッチング
            matching_words = [word for word in query_words if word in text]
            if matching_words:
                analysis["relevance_indicators"].append({
                    "law_title": result.get("law_title"),
                    "matching_words": matching_words,
                    "match_ratio": len(matching_words) / len(query_words) if query_words else 0
                })
            
            # 未定義用語の検出
            for term in age_terms:
                if term in text and "定める" in text:
                    analysis["undefined_terms"].append({
                        "term": term,
                        "law_title": result.get("law_title"),
                        "context": text[:100]
                    })
            
            # 他法令への参照を検出
            law_pattern = r'([一-龥]+法)(?:第[一-九十百千万]+条)?'
            found_laws = re.findall(law_pattern, text)
            for found_law in found_laws:
                if found_law != result.get("law_title"):
                    law_references.append({
                        "from_law": result.get("law_title"),
                        "to_law": found_law,
                        "context": text[:100]
                    })
        
        # 重複を除去
        analysis["referenced_laws"] = list({ref["to_law"]: ref for ref in law_references}.values())
        
        # 次のアクションを提案
        if len(law_count) == 1:
            # 単一の法令に集中
            law_id = list(law_count.keys())[0]
            analysis["suggested_actions"].append({
                "action": "get_full_law",
                "reason": "検索結果が単一の法令に集中している",
                "law_id": law_id,
                "law_title": law_count[law_id]["title"]
            })
        elif len(law_count) > 5:
            # 結果が分散
            analysis["suggested_actions"].append({
                "action": "narrow_search",
                "reason": "検索結果が複数の法令に分散している",
                "suggestion": "より具体的なキーワードで絞り込み"
            })
        
        # 未定義用語がある場合
        if analysis["undefined_terms"]:
            for term_info in analysis["undefined_terms"]:
                analysis["suggested_actions"].append({
                    "action": "search_definition",
                    "reason": f"'{term_info['term']}'の定義が必要",
                    "suggestion": f"'{term_info['term']} 定義'で検索"
                })
        
        # 参照法令がある場合
        if analysis["referenced_laws"]:
            for ref in analysis["referenced_laws"][:3]:  # 上位3件
                analysis["suggested_actions"].append({
                    "action": "search_referenced_law",
                    "reason": f"他の法令（{ref['to_law']}）が参照されている",
                    "target_law": ref["to_law"]
                })
        
        # 年齢に関するクエリの場合
        if any(word in original_query for word in ["歳", "年齢", "何歳"]):
            analysis["suggested_actions"].append({
                "action": "search_age_definitions",
                "reason": "年齢に関する質問",
                "suggestion": "年齢区分の定義を確認（幼児、児童等）"
            })
        
        return json.dumps(analysis, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": "analysis_failed",
            "message": str(e)
        }, ensure_ascii=False)

if __name__ == "__main__":
    # MCPサーバーを起動
    mcp.run(transport='stdio')
    
# 使用例：
# 1. AIが get_search_guidance() を呼び出してガイダンスを確認
# 2. 自然言語クエリから適切なキーワードを抽出
# 3. search_laws_by_keyword() で初期検索
# 4. analyze_search_results() で結果を分析
# 5. 必要に応じて追加検索（定義の確認、参照法令の検索等）
# 6. 最終的な回答を生成（仮定や推論を明示）