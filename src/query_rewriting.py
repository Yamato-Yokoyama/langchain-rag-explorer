"""
src/query_rewriting.py

クエリを retrieval に効きやすい形に変換するユーティリティ集。
複数の戦略を並列に並べて、実験で比較する用。

Called by:
    - src/rag_pipeline.py の search() 内で条件付き呼び出し

Depends on:
    - langchain_google_genai (LLM)
"""

from langchain.messages import HumanMessage, SystemMessage

def expand_query_to_definition(query: str, llm) -> str:
    """
    ユーザーの質問を、定義的な平叙文に拡張する。
    Speech Act ミスマッチ(Directive query vs Assertive chunks)への対処。
    
    Input:
        query: ユーザーの元クエリ(例: "Q-principle って何?")
        llm: ChatGoogleGenerativeAI インスタンス
    
    Output:
        str: 拡張されたクエリ(例: "Q-principle の定義。Neo-Gricean...")
    
    なぜ:
        - 素朴 embedding 検索で発見された Speech Act ミスマッチへの構造的対処
        - Directive(質問) → Assertive(定義的平叙文) の翻訳を LLM に任せる
        - retrieval の cosine score が上がる = Q-principle chunk が上位に来る
    """
    
    sytem_prompt ="""
    あなたは検索クエリの拡張を担当します。
    ユーザーの質問を、embedding ベースの検索で関連文書がヒットしやすい形に書き換えてください。

    ルール:
    - 質問文ではなく、定義的な平叙文の形にする
    - 関連する専門用語、同義語、期待される答えの語彙を含める
    - 地名が出てきたら、より広い/別の地域名も候補に含める(例: 日本 → Asia-Pacific, APAC)
    - 役職名が出てきたら、会社によって呼び方が違う類義の役職名も候補に含める
      (例: VP → 統括, ディレクター, 部門責任者, General Manager)
    - 1-2 文で簡潔に
    - 質問に答えるのではなく、拡張だけを返す

    例:
    入力: "光合成って何?"
    出力: "光合成の定義とプロセス。植物が光エネルギーを化学エネルギーに変換する過程で、二酸化炭素と水から糖と酸素を生成する反応。"

    入力: "Docker のメリット?"
    出力: "Docker のメリットと利点。コンテナ化技術による環境の一貫性、デプロイの容易さ、リソース効率の向上。"

    入力: "DeepL Japanの担当者は誰?"
    出力: "DeepL Japan、日本、またはAsia-Pacific(APAC)地域を統括する担当者。役職はVice President、Director、General Manager、または日本語で統括・代表・責任者と呼ばれる立場を含む。"

    入力: "SAPのVPとつながっていますか?"
    出力: "SAPのVice President(VP)、または日本語で統括・部門責任者・ディレクターと呼ばれる役職の人物とのつながり。"
    """
    
    message = [
        SystemMessage(content=sytem_prompt),
        HumanMessage(content=f"入力： {query}\n出力:"),
    ]
    
    response = llm.invoke(message)

    return response.text.strip()
