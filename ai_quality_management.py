import asyncio
import json
from typing import Any, Sequence

from mcp.server import Server
import mcp.types as types

# 品質特性の定義データ
QUALITY_CHARACTERISTICS = {
    # コンポーネント品質
    "requirements-satisfiability": {
        "name": "要求満足性",
        "english": "Requirements Satisfiability",
        "description": "LLM利用AIシステムに期待されるソフトウェア要求を満たすこと",
        "review_purpose": "システムが当初の要求や仕様を満たしているかを確認する",
        "genai_context": "生成AIシステムでは確率的な動作のため、従来のソフトウェアより要求の定義と検証が困難",
        "check_points": [
            "機能要求が明確に定義され、実装されているか",
            "品質要求（性能、セキュリティ等）が満たされているか",
            "暗黙の要求も含めて漏れがないか"
        ],
        "subcategories": {
            "functional-requirements": {
                "description": "機能要求満足性：明示的および暗黙に与えられる機能要求を満たすこと",
                "review_focus": "システムが期待された機能を提供しているか",
                "examples": ["質問応答機能が仕様通り動作する", "文書要約が期待される品質で実行される"]
            },
            "quality-requirements": {
                "description": "品質要求満足性：機能外要求（品質要求）を満たすこと",
                "review_focus": "性能、セキュリティ、使いやすさ等の非機能要求が満たされているか",
                "examples": ["応答時間が要求内", "セキュリティ基準を満たす", "ユーザビリティが十分"]
            }
        }
    },
    "reliability": {
        "name": "信頼性",
        "english": "Reliability",
        "description": "期待される機能を実行すること、つまり、所与の仕様を満たすこと",
        "review_purpose": "システムが継続的に安定して動作し、予期された通りに機能するかを確認する",
        "genai_context": "LLMの確率的性質により、同じ入力でも異なる出力が生成されるため、従来システムより信頼性の定義が複雑",
        "check_points": [
            "同一入力に対する出力の一貫性",
            "異常入力に対する適切な対応",
            "長時間運用での安定性",
            "想定外の状況での振る舞い"
        ],
        "subcategories": {
            "maturity": {
                "description": "成熟性：想定された作動条件の下で、期待する信頼性を満足すること",
                "review_focus": "通常の使用条件下でシステムが安定動作するか",
                "examples": ["日常的な質問に対して適切に応答", "想定されたユーザー数で安定動作"]
            },
            "robustness": {
                "description": "ロバスト性：通常期待する基準データから外れたデータが入力された時の振舞いの度合い",
                "review_focus": "想定外の入力に対してもシステムが適切に対応できるか",
                "examples": ["文字化けした入力への適切な応答", "極端に長い文章の処理", "専門外分野への謙虚な対応"],
                "negative_examples": ["異常入力でのシステムクラッシュ", "意味不明な出力の生成", "想定外入力での無応答"]
            },
            "output-consistency": {
                "description": "出力一貫性：同一入力を繰り返したとき、入力に対する出力内容が整合していること",
                "review_focus": "同じ質問に対して一貫した品質の回答が得られるか",
                "examples": ["同じ質問への論理的に一貫した回答", "出力形式・構造の統一性", "事実情報の一貫性"],
                "negative_examples": ["同じ質問への矛盾した回答", "回答品質の大幅なばらつき", "形式の不統一"]
            },
            "progress": {
                "description": "進行性：想定外に停止する（デッドロック）、想定外の繰り返し閉路に陥る（ライブロック）といった不適切な状況に陥らないこと",
                "review_focus": "システムが正常に処理を進行し、停止状態に陥らないか",
                "examples": ["長い処理でもタイムアウトで適切に終了", "無限ループに陥らない設計"]
            },
            "availability": {
                "description": "可用性：期待する使用の状況下で、LLM利用AIシステムが、意図した機能振舞いを示し、運用可能なこと",
                "review_focus": "必要な時にシステムが利用可能な状態にあるか",
                "examples": ["営業時間中の継続稼働", "メンテナンス時間以外の安定提供"]
            },
            "fault-tolerance": {
                "description": "耐故障性：故障にもかかわらず、LLM利用AIシステムが、意図したように運用できること",
                "review_focus": "部分的な故障が発生してもシステム全体が継続動作するか",
                "examples": ["一部コンポーネント故障時の縮退運転", "外部API障害時の代替動作"]
            },
            "resilience": {
                "description": "回復性：故障によって処理を中断した時に、直接影響を受けた情報を回復し、システムの状態を復元できること",
                "review_focus": "故障からの回復が適切に行われるか",
                "examples": ["システム再起動後の状態復元", "データ整合性の回復"]
            }
        }
    },
    "interaction-capability": {
        "name": "インタラクション性",
        "english": "Interaction Capability", 
        "description": "期待される状況で、エンドユーザー自身が想定するようにLLM利用AIシステムを利用できること",
        "review_purpose": "ユーザーがシステムを直感的で効果的に利用できるかを確認する",
        "genai_context": "対話型AIシステムでは、ユーザーとの自然な対話が重要で、従来のGUIとは異なるインタラクション設計が必要",
        "check_points": [
            "ユーザーがシステムの能力と限界を理解できるか",
            "多様なユーザーが利用可能か",
            "ユーザーがシステムを制御できるか",
            "システムの判断根拠が説明されるか"
        ],
        "subcategories": {
            "appropriateness-recognizability": {
                "description": "適切度認識性：エンドユーザーの期待に対して、LLM利用AIシステムが適切であるかを、エンドユーザーが事前に認識できること",
                "review_focus": "ユーザーがシステムの適用範囲と限界を理解できるか",
                "examples": ["システムの得意分野と不得意分野の明示", "利用可能な機能の明確な説明"]
            },
            "accessibility": {
                "description": "アクセシビリティ：幅広い範囲の心身特性および能力を持つエンドユーザーがLLM利用AIシステムを利用できること",
                "review_focus": "多様なユーザーがシステムを利用できるか",
                "examples": ["視覚障害者向けスクリーンリーダー対応", "多言語対応", "シンプルな操作インターフェース"]
            },
            "controllability": {
                "description": "可制御性：LLM利用AIシステムが運用操作しやすく、制御しやすくする技術的な特性を持つこと",
                "review_focus": "ユーザーがシステムの動作を制御できるか",
                "examples": ["出力の調整機能", "処理の停止・再開機能", "設定のカスタマイズ"]
            },
            "explicability": {
                "description": "説明性：LLM利用AIシステムが出力コンテンツを生成した理由に関わる情報を補って提示できること",
                "review_focus": "システムの判断根拠や推論過程が説明されるか",
                "examples": ["回答の根拠となる情報源の提示", "判断プロセスの説明", "信頼度の表示"]
            },
            "learnability": {
                "description": "習得性：期待される状況で、エンドユーザーがLLM利用AIシステムを利用しやすいこと",
                "review_focus": "ユーザーがシステムの使い方を容易に習得できるか",
                "examples": ["直感的な操作方法", "ガイドやチュートリアルの提供", "エラー時の適切なフィードバック"]
            }
        }
    },
    "security": {
        "name": "セキュリティ",
        "english": "Security",
        "description": "LLM利用AIシステムが管理する情報を保護すること",
        "review_purpose": "システムが情報資産を適切に保護し、セキュリティ脅威に対応できるかを確認する",
        "genai_context": "プロンプトインジェクションや訓練データ漏洩など、生成AI特有のセキュリティリスクが存在",
        "check_points": [
            "認証・認可機能の実装状況（ユーザー管理、権限制御）",
            "プロンプトインジェクション攻撃の検知・防止機能",
            "システムプロンプトや機密データの漏洩防止対策",
            "操作ログ、アクセスログの適切な記録と監視体制"
        ],
        "subcategories": {
            "access-control": {
                "description": "アクセス制御性：利用許可条件にしたがって情報を保護し処理できること",
                "review_focus": "認証・認可機能が適切に実装され、不正アクセスを防止できているか",
                "examples": ["多要素認証の実装", "役割ベースの権限管理", "APIキーの適切な管理"],
                "negative_examples": ["認証なしでの機能アクセス", "権限昇格の脆弱性", "機密データへの無制限アクセス"]
            },
            "intervenability": {
                "description": "介入性：稼働中のLLM利用AIシステムの動作に、外部から介入し、システムの状態を安定させること",
                "review_focus": "管理者がシステムの動作を適切に制御・介入できる仕組みがあるか",
                "examples": ["管理者用の緊急停止ボタン", "リアルタイムでの出力制御", "問題検知時の自動介入機能"],
                "negative_examples": ["暴走時に停止できない", "管理者権限での制御機能がない", "介入方法が不明確"]
            },
            "authenticity": {
                "description": "真正性：制御対象に関わる情報ならびにアクセス主体に関わる情報の身元が明らかなこと",
                "review_focus": "データやユーザーの身元・出典が確実に確認できる仕組みがあるか",
                "examples": ["デジタル証明書による身元確認", "データの電子署名", "信頼できる情報源の明示"],
                "negative_examples": ["出典不明のデータ使用", "なりすましアクセスの可能性", "偽装された情報の混入"]
            },
            "accountability": {
                "description": "責任追跡性：LLM利用AIシステムの出力コンテンツを生成した理由や要因を再現し提示できること",
                "review_focus": "システムの判断や動作を事後的に追跡・検証できる仕組みがあるか",
                "examples": ["詳細な操作ログの保存", "出力生成時の入力・設定の記録", "意思決定プロセスの可視化"],
                "negative_examples": ["操作履歴の記録なし", "出力根拠の説明不可", "責任の所在が不明確"]
            }
        }
    },
    "safety": {
        "name": "安全性",
        "english": "Safety",
        "description": "設計者が許容できるレベルまでリスク低減した上で、かつ、定められた条件下で、LLM利用AIシステムが、外部に危害を及ぼす状態に陥らないこと",
        "review_purpose": "システムが外部に危害を及ぼすリスクを適切に管理できているかを確認する",
        "genai_context": "生成AIは有害なコンテンツや誤情報を生成するリスクがあり、社会的影響を考慮した安全性確保が重要",
        "check_points": [
            "有害・不適切コンテンツの生成防止機能の実装状況",
            "システム故障時の安全な動作停止メカニズム",
            "AI生成コンテンツの明確な識別・表示機能",
            "想定外入力に対する適切な制限・フィルタリング機能"
        ],
        "subcategories": {
            "input-constraint": {
                "description": "入力制限性：LLM利用AIシステムが定められた条件下で作動する際に、危険な状態に至るような入力を制限すること",
                "review_focus": "危険な結果を招く可能性のある入力が効果的に検知・制限されているか",
                "examples": ["暴力的コンテンツ生成指示の拒否", "個人情報抽出を狙った質問の無効化", "システム制御を試みる入力の検知"],
                "negative_examples": ["有害指示の素通り", "脱獄（jailbreak）攻撃の成功", "システムプロンプト改竄の許可"]
            },
            "fail-safe": {
                "description": "フェイルセーフ性：LLM利用AIシステムが故障発生に際して、外部への危害が生じるような不適切な出力を行わないこと",
                "review_focus": "システム異常時に安全な状態を維持できるか",
                "examples": ["エラー時の「分からない」応答", "過負荷時の安全な処理停止", "異常検知時のフェイルセーフモード移行"],
                "negative_examples": ["エラー時の有害出力", "システム暴走状態の継続", "異常状態での不適切な応答継続"]
            },
            "non-repudiation": {
                "description": "否認防止性：LLM利用AIシステムの出力コンテンツが、機械学習AIの技術を用いて生成されたことを確認できること",
                "review_focus": "AI生成コンテンツであることが明確に識別・証明できるか",
                "examples": ["「AI生成」ラベルの自動付与", "生成時のメタデータ記録", "透かし技術の実装"],
                "negative_examples": ["AI生成の表示なし", "人間作成との区別不可", "生成履歴の記録なし"]
            }
        }
    },
    "privacy": {
        "name": "プライバシー",
        "english": "Information Privacy",
        "description": "パーソナルデータの取り扱いに関して、想定外の情報プライバシー漏洩が生じないこと",
        "review_purpose": "個人情報やプライベートなデータが適切に保護されているかを確認する",
        "genai_context": "訓練データからの個人情報漏洩やユーザー入力の不適切な利用など、生成AI特有のプライバシーリスクが存在",
        "check_points": [
            "個人情報の収集・利用目的の明確化と同意取得状況",
            "訓練データからの個人情報漏洩防止機能の実装",
            "ユーザー入力データの暗号化・匿名化処理",
            "GDPR等のプライバシー法規制への準拠状況"
        ],
        "examples": ["出力での個人名・住所・電話番号の自動マスキング", "訓練データの事前匿名化処理", "ユーザー会話履歴の適切な管理"],
        "negative_examples": ["実在人物の個人情報をそのまま出力", "削除要求への対応不備", "同意なしでの個人データ利用"],
        "subcategories": {}
    },
    "fairness": {
        "name": "公平性",
        "english": "Algorithmic Fairness",
        "description": "要配慮属性を含むデータの取り扱いに関して、想定外の偏りが生じないこと",
        "review_purpose": "システムが特定のグループに対して不当な差別や偏見を示さないかを確認する",
        "genai_context": "訓練データの偏りが出力に反映され、性別・人種・年齢等による不公平な判断を生成するリスクがある",
        "check_points": [
            "性別・人種・年齢・宗教等による出力の偏り検査",
            "多様性を考慮した回答生成の確認",
            "ステレオタイプや差別的表現の検知・防止機能",
            "公平性メトリクスによる定期的な評価実施"
        ],
        "examples": ["職業紹介で性別に関係なく平等な提案", "多様な背景の人物を含む画像生成", "文化的偏見を避けた説明"],
        "negative_examples": ["「看護師は女性」等のステレオタイプ出力", "特定人種への偏見を含む回答", "年齢による能力の決めつけ"],
        "subcategories": {}
    },
    "performance-efficiency": {
        "name": "性能効率性",
        "english": "Performance Efficiency",
        "description": "LLM利用AIシステムが、想定された状況下で作動する度合いに応じて、期待する量の計算資源を使用すること",
        "review_purpose": "システムが適切な性能で動作し、計算資源を効率的に使用しているかを確認する",
        "genai_context": "大規模言語モデルは計算集約的で、推論時間やメモリ使用量が従来システムより大きくなりがち",
        "check_points": [
            "応答時間が許容範囲内か",
            "計算資源の使用量が適切か",
            "スケーラビリティが確保されているか",
            "性能ボトルネックの特定と対策"
        ],
        "subcategories": {
            "time-behavior": {
                "description": "時間効率性：LLM利用AIシステムが機能を実行するとき、期待通りの応答時間・処理時間・スループットを示すこと",
                "review_focus": "システムの応答性が要求を満たしているか",
                "examples": ["質問への数秒以内の応答", "バッチ処理の適切な処理時間", "同時ユーザー数に対する性能維持"]
            },
            "resource-utilization": {
                "description": "資源効率性：LLM利用AIシステムが機能を実行するとき、計算資源の量を期待通りに使用し、過剰な計算資源を使用しないこと",
                "review_focus": "計算資源が効率的に使用されているか",
                "examples": ["GPU/CPUの適切な使用率", "メモリ使用量の最適化", "不要な計算の削減"]
            }
        }
    },
    "portability": {
        "name": "移植性",
        "english": "Portability",
        "description": "LLM利用AIシステムを、他の運用環境あるいは利用環境に移すのが容易であること",
        "review_purpose": "システムが異なる環境間で容易に移行・動作できるかを確認する",
        "genai_context": "クラウド環境の変更、エッジデバイスへの展開、異なるモデルへの切り替えなど、生成AIシステム特有の移植性要件がある",
        "check_points": [
            "異なるクラウドプラットフォーム間での移行可能性",
            "オンプレミスとクラウド間での移植性",
            "異なるハードウェア環境での動作",
            "設定や依存関係の標準化"
        ],
        "examples": ["AWS→Azure間でのシステム移行", "CPUからGPU環境への移植", "異なるLLMモデルへの切り替え対応"],
        "subcategories": {}
    },
    "maintainability": {
        "name": "保守性",
        "english": "Maintainability",
        "description": "期待される状況で、保守者がLLM利用AIシステムを進化発展させることの容易さ",
        "review_purpose": "システムの保守・改善・拡張が容易に行えるかを確認する",
        "genai_context": "モデルの更新、プロンプトの調整、新機能追加など、生成AIシステム特有の保守要件がある",
        "check_points": [
            "システム構成の理解しやすさ",
            "コンポーネント間の依存関係の明確さ",
            "変更の影響範囲の特定容易性",
            "テスト・検証の自動化"
        ],
        "subcategories": {
            "modularity": {
                "description": "モジュール性：LLM利用AIシステムを構成するアーキテクチャコンポーネント互いの依存関係を明らかにすること",
                "review_focus": "システムが適切にモジュール化され、依存関係が明確か",
                "examples": ["LLMエンジンとビジネスロジックの分離", "プロンプト管理の独立化", "API境界の明確な定義"]
            },
            "modifiability": {
                "description": "修正性：LLM利用AIシステムならびに構成コンポーネントの修正が容易なこと",
                "review_focus": "システムの変更・修正が容易に行えるか",
                "examples": ["プロンプトの更新手順の簡素化", "モデル変更時の影響最小化", "設定変更の自動反映"]
            },
            "testability": {
                "description": "試験性：LLM利用AIシステムならびに構成コンポーネントの試験が容易なこと",
                "review_focus": "システムのテストが効率的に実行できるか",
                "examples": ["出力品質の自動評価", "回帰テストの仕組み", "A/Bテストの実施基盤"]
            }
        }
    }
}

# データ品質の定義
DATA_QUALITY_CHARACTERISTICS = {
    "individual-data-points": {
        "name": "個々のデータ点の品質観点",
        "description": "個々のデータ点が満たすべき品質観点",
        "review_purpose": "訓練・評価データの各データ点が適切な品質を満たしているかを確認する",
        "genai_context": "LLMの出力品質は訓練データの質に大きく依存するため、個々のデータ点の品質確保が重要",
        "check_points": [
            "事実確認済みデータの割合と検証プロセス",
            "必須属性・フィールドの欠損率",
            "データ間の論理的整合性チェック",
            "データの鮮度（更新頻度・取得時期）の確認"
        ],
        "subcategories": {
            "accuracy": {
                "description": "正確性：構文上（形式上）ならびに意味上、正しい表現を持つこと",
                "review_focus": "データが事実に即して正確であるか",
                "examples": ["文法的に正しい文章", "事実と一致する数値・日付", "専門用語の正確な使用"],
                "negative_examples": ["明らかな文法誤り", "事実と異なる情報", "意味不明な文章"]
            },
            "completeness": {
                "description": "完全性：データ点が複数の属性から構成される場合、すべての属性が欠損していないこと",
                "review_focus": "必要な情報が漏れなく含まれているか",
                "examples": ["質問と回答のペアで両方が存在", "メタデータの完全な記載", "必須フィールドの欠損なし"]
            },
            "consistency": {
                "description": "一貫性：データ点が複数の属性から構成される場合、すべての属性の値が整合していること",
                "review_focus": "データ内の情報が矛盾していないか",
                "examples": ["日付と曜日の整合", "数値データの単位統一", "カテゴリ分類の一貫性"]
            },
            "credibility": {
                "description": "信憑性：すべての属性の値が、データ利用者にとって、真とみなせること",
                "review_focus": "データの信頼性が確保されているか",
                "examples": ["信頼できる情報源からの取得", "専門家による検証済み", "偽情報の除外"]
            },
            "currentness": {
                "description": "最新性：すべての属性が最新の値になっていること",
                "review_focus": "データが適切な時点のものであるか",
                "examples": ["最新の法律・制度に基づく情報", "廃止された情報の除外", "タイムスタンプの適切性"]
            },
            "precision": {
                "description": "精度：すべての属性の値が期待される数値精度をもつこと",
                "review_focus": "数値データの精度が適切であるか",
                "examples": ["小数点以下の桁数統一", "測定精度の明確化", "丸め誤差の管理"]
            },
            "data-usage-control": {
                "description": "利用性：すべての属性の値が利用承認されていること",
                "review_focus": "データの利用権限が適切に確保されているか",
                "examples": ["著作権のクリア", "利用許諾の取得", "プライバシー保護の確認"]
            },
            "compliance": {
                "description": "標準適合性：すべての属性の値が規則に適合していること",
                "review_focus": "関連する規則や標準に準拠しているか",
                "examples": ["業界標準への適合", "法規制の遵守", "社内ガイドラインの準拠"]
            }
        }
    },
    "dataset-quality": {
        "name": "データセットの品質観点",
        "description": "データの集まりとしてのデータセットが満たすべき品質観点",
        "review_purpose": "訓練・評価用データセット全体として適切な品質を満たしているかを確認する",
        "genai_context": "LLMの性能は個々のデータだけでなく、データセット全体の構成や偏りに大きく影響される",
        "check_points": [
            "対象ドメインのカテゴリ網羅率と分布バランス",
            "データ収集・アノテーション基準の一貫性",
            "サンプリング手法の適切性と偏りの有無",
            "データソースの信頼性と来歴情報の完全性"
        ],
        "subcategories": {
            "representativeness": {
                "description": "代表性：カテゴリーごとに適切なデータを抽出し、全体を合わせてデータセットにすること",
                "review_focus": "対象領域を適切に代表するデータが偏りなく含まれているか",
                "examples": ["全業界カテゴリの均等な含有", "地域・言語の多様性確保", "難易度分布の適切性"],
                "negative_examples": ["特定分野のみに偏ったデータ", "一部地域・言語の欠如", "簡単な例ばかりでの構成"]
            },
            "overlap": {
                "description": "重複性：カテゴリーと隣接カテゴリーの間で、データの一部を共有すること",
                "review_focus": "カテゴリ間で適切なデータ共有があるか",
                "examples": ["境界領域のデータ包含", "関連分野の橋渡し情報", "グラデーション的なデータ配置"]
            },
            "sample-selection": {
                "description": "標本選択性：経験分布を再現するように、データを選択すること",
                "review_focus": "実世界の分布を適切に反映しているか",
                "examples": ["実際の使用頻度に応じた選択", "現実的な難易度分布", "自然な言語使用パターンの反映"]
            },
            "consistency": {
                "description": "一貫性：期待する品質を満たす処理が、定められた方針の下に実施されていること",
                "review_focus": "データセット構築が一貫した方針で行われているか",
                "examples": ["統一されたアノテーション基準", "一貫したデータ収集方法", "同一の品質チェック基準"]
            },
            "provenance": {
                "description": "来歴性：信憑性・真正性を満たすデータから構成されるデータセットが持つ性質",
                "review_focus": "データの出典と履歴が適切に管理されているか",
                "examples": ["データソースの明確な記録", "加工履歴の追跡可能性", "品質検証プロセスの記録"]
            },
            "dataset-newness": {
                "description": "最新性：最新性を満たすデータから構成されること",
                "review_focus": "データセットが適切な時期のデータで構成されているか",
                "examples": ["最新の知識・情報の反映", "古い情報の適切な更新", "時代に応じた内容の調整"]
            }
        }
    }
}

# Create MCP server instance
server = Server("genai-quality-management")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Return a list of available tools for GenAI quality management.
    """
    return [
        types.Tool(
            name="list_quality_characteristics",
            description="生成AIシステムの品質特性一覧を取得する",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_quality_characteristic_detail",
            description="指定した品質特性の詳細情報を取得する",
            inputSchema={
                "type": "object",
                "properties": {
                    "characteristic_id": {
                        "type": "string",
                        "description": "品質特性のID（例：reliability, security, safety等）"
                    }
                },
                "required": ["characteristic_id"]
            }
        ),
        types.Tool(
            name="get_subcategory_detail",
            description="指定した品質特性のサブカテゴリの詳細情報を取得する",
            inputSchema={
                "type": "object",
                "properties": {
                    "characteristic_id": {
                        "type": "string",
                        "description": "品質特性のID"
                    },
                    "subcategory_id": {
                        "type": "string",
                        "description": "サブカテゴリのID（例：robustness, output-consistency等）"
                    }
                },
                "required": ["characteristic_id", "subcategory_id"]
            }
        ),
        types.Tool(
            name="list_data_quality_characteristics",
            description="データ品質の特性一覧を取得する",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_data_quality_detail",
            description="指定したデータ品質特性の詳細情報を取得する",
            inputSchema={
                "type": "object",
                "properties": {
                    "data_quality_id": {
                        "type": "string",
                        "description": "データ品質特性のID（individual-data-points または dataset-quality）"
                    }
                },
                "required": ["data_quality_id"]
            }
        ),
        types.Tool(
            name="get_data_quality_subcategory_detail",
            description="指定したデータ品質特性のサブカテゴリの詳細情報を取得する",
            inputSchema={
                "type": "object",
                "properties": {
                    "data_quality_id": {
                        "type": "string",
                        "description": "データ品質特性のID"
                    },
                    "subcategory_id": {
                        "type": "string",
                        "description": "サブカテゴリのID（例：accuracy, completeness等）"
                    }
                },
                "required": ["data_quality_id", "subcategory_id"]
            }
        ),
        types.Tool(
            name="search_quality_characteristics",
            description="キーワードで品質特性を検索する",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "検索するキーワード（日本語または英語）"
                    }
                },
                "required": ["keyword"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """
    Handle tool execution for GenAI quality management.
    """
    
    if name == "list_quality_characteristics":
        result = "# 生成AIシステムの品質特性一覧\n\n"
        for char_id, char_data in QUALITY_CHARACTERISTICS.items():
            result += f"## {char_data['name']} ({char_data['english']})\n"
            result += f"**ID**: {char_id}\n"
            result += f"**説明**: {char_data['description']}\n"
            result += f"**生成AI特有の観点**: {char_data['genai_context']}\n\n"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "get_quality_characteristic_detail":
        characteristic_id = arguments.get("characteristic_id")
        
        if characteristic_id not in QUALITY_CHARACTERISTICS:
            error_msg = f"エラー: 品質特性ID '{characteristic_id}' が見つかりません。\n利用可能なID: {list(QUALITY_CHARACTERISTICS.keys())}"
            return [types.TextContent(type="text", text=error_msg)]
        
        char_data = QUALITY_CHARACTERISTICS[characteristic_id]
        result = f"# {char_data['name']} ({char_data['english']})\n\n"
        result += f"**説明**: {char_data['description']}\n\n"
        result += f"**レビュー目的**: {char_data['review_purpose']}\n\n"
        result += f"**生成AI特有の観点**: {char_data['genai_context']}\n\n"
        
        result += "## チェックポイント\n"
        for point in char_data['check_points']:
            result += f"- {point}\n"
        result += "\n"
        
        if char_data.get('examples'):
            result += "## 良い例\n"
            for example in char_data['examples']:
                result += f"- {example}\n"
            result += "\n"
        
        if char_data.get('negative_examples'):
            result += "## 悪い例\n"
            for example in char_data['negative_examples']:
                result += f"- {example}\n"
            result += "\n"
        
        if char_data['subcategories']:
            result += "## サブカテゴリ\n"
            for sub_id, sub_data in char_data['subcategories'].items():
                result += f"### {sub_id}\n"
                result += f"**説明**: {sub_data['description']}\n"
                result += f"**レビュー観点**: {sub_data['review_focus']}\n"
                if sub_data.get('examples'):
                    result += "**良い例**: " + ", ".join(sub_data['examples']) + "\n"
                if sub_data.get('negative_examples'):
                    result += "**悪い例**: " + ", ".join(sub_data['negative_examples']) + "\n"
                result += "\n"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "get_subcategory_detail":
        characteristic_id = arguments.get("characteristic_id")
        subcategory_id = arguments.get("subcategory_id")
        
        if characteristic_id not in QUALITY_CHARACTERISTICS:
            error_msg = f"エラー: 品質特性ID '{characteristic_id}' が見つかりません。"
            return [types.TextContent(type="text", text=error_msg)]
        
        char_data = QUALITY_CHARACTERISTICS[characteristic_id]
        if subcategory_id not in char_data['subcategories']:
            error_msg = f"エラー: サブカテゴリID '{subcategory_id}' が品質特性 '{characteristic_id}' に見つかりません。\n利用可能なサブカテゴリ: {list(char_data['subcategories'].keys())}"
            return [types.TextContent(type="text", text=error_msg)]
        
        sub_data = char_data['subcategories'][subcategory_id]
        result = f"# {subcategory_id} ({char_data['name']}のサブカテゴリ)\n\n"
        result += f"**説明**: {sub_data['description']}\n\n"
        result += f"**レビュー観点**: {sub_data['review_focus']}\n\n"
        
        if sub_data.get('examples'):
            result += "## 良い例\n"
            for example in sub_data['examples']:
                result += f"- {example}\n"
            result += "\n"
        
        if sub_data.get('negative_examples'):
            result += "## 悪い例\n"
            for example in sub_data['negative_examples']:
                result += f"- {example}\n"
            result += "\n"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "list_data_quality_characteristics":
        result = "# データ品質特性一覧\n\n"
        for dq_id, dq_data in DATA_QUALITY_CHARACTERISTICS.items():
            result += f"## {dq_data['name']}\n"
            result += f"**ID**: {dq_id}\n"
            result += f"**説明**: {dq_data['description']}\n"
            result += f"**生成AI特有の観点**: {dq_data['genai_context']}\n\n"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "get_data_quality_detail":
        data_quality_id = arguments.get("data_quality_id")
        
        if data_quality_id not in DATA_QUALITY_CHARACTERISTICS:
            error_msg = f"エラー: データ品質特性ID '{data_quality_id}' が見つかりません。\n利用可能なID: {list(DATA_QUALITY_CHARACTERISTICS.keys())}"
            return [types.TextContent(type="text", text=error_msg)]
        
        dq_data = DATA_QUALITY_CHARACTERISTICS[data_quality_id]
        result = f"# {dq_data['name']}\n\n"
        result += f"**説明**: {dq_data['description']}\n\n"
        result += f"**レビュー目的**: {dq_data['review_purpose']}\n\n"
        result += f"**生成AI特有の観点**: {dq_data['genai_context']}\n\n"
        
        result += "## チェックポイント\n"
        for point in dq_data['check_points']:
            result += f"- {point}\n"
        result += "\n"
        
        if dq_data['subcategories']:
            result += "## サブカテゴリ\n"
            for sub_id, sub_data in dq_data['subcategories'].items():
                result += f"### {sub_id}\n"
                result += f"**説明**: {sub_data['description']}\n"
                result += f"**レビュー観点**: {sub_data['review_focus']}\n"
                if sub_data.get('examples'):
                    result += "**良い例**: " + ", ".join(sub_data['examples']) + "\n"
                if sub_data.get('negative_examples'):
                    result += "**悪い例**: " + ", ".join(sub_data['negative_examples']) + "\n"
                result += "\n"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "get_data_quality_subcategory_detail":
        data_quality_id = arguments.get("data_quality_id")
        subcategory_id = arguments.get("subcategory_id")
        
        if data_quality_id not in DATA_QUALITY_CHARACTERISTICS:
            error_msg = f"エラー: データ品質特性ID '{data_quality_id}' が見つかりません。"
            return [types.TextContent(type="text", text=error_msg)]
        
        dq_data = DATA_QUALITY_CHARACTERISTICS[data_quality_id]
        if subcategory_id not in dq_data['subcategories']:
            error_msg = f"エラー: サブカテゴリID '{subcategory_id}' がデータ品質特性 '{data_quality_id}' に見つかりません。\n利用可能なサブカテゴリ: {list(dq_data['subcategories'].keys())}"
            return [types.TextContent(type="text", text=error_msg)]
        
        sub_data = dq_data['subcategories'][subcategory_id]
        result = f"# {subcategory_id} ({dq_data['name']}のサブカテゴリ)\n\n"
        result += f"**説明**: {sub_data['description']}\n\n"
        result += f"**レビュー観点**: {sub_data['review_focus']}\n\n"
        
        if sub_data.get('examples'):
            result += "## 良い例\n"
            for example in sub_data['examples']:
                result += f"- {example}\n"
            result += "\n"
        
        if sub_data.get('negative_examples'):
            result += "## 悪い例\n"
            for example in sub_data['negative_examples']:
                result += f"- {example}\n"
            result += "\n"
        
        return [types.TextContent(type="text", text=result)]
    
    elif name == "search_quality_characteristics":
        keyword = arguments.get("keyword", "").lower()
        
        if not keyword:
            return [types.TextContent(type="text", text="エラー: 検索キーワードが指定されていません。")]
        
        results = []
        
        # 品質特性を検索
        for char_id, char_data in QUALITY_CHARACTERISTICS.items():
            if (keyword in char_data['name'].lower() or 
                keyword in char_data['english'].lower() or 
                keyword in char_data['description'].lower() or
                keyword in char_data['genai_context'].lower()):
                results.append(f"**品質特性**: {char_data['name']} ({char_data['english']}) - ID: {char_id}")
        
        # データ品質特性を検索
        for dq_id, dq_data in DATA_QUALITY_CHARACTERISTICS.items():
            if (keyword in dq_data['name'].lower() or 
                keyword in dq_data['description'].lower() or
                keyword in dq_data['genai_context'].lower()):
                results.append(f"**データ品質特性**: {dq_data['name']} - ID: {dq_id}")
        
        if results:
            result_text = f"# キーワード '{keyword}' の検索結果\n\n" + "\n".join(results)
        else:
            result_text = f"キーワード '{keyword}' に該当する品質特性が見つかりませんでした。"
        
        return [types.TextContent(type="text", text=result_text)]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main entry point for the server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())