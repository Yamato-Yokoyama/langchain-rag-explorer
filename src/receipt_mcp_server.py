"""
src/receipt_mcp_server.py

レシートPDF/画像 → 構造化JSON、を公開するMCPサーバーの本実装。
hello_mcp.pyで確認した「@mcp.tool()を付けるだけ」の型を、実際のレシート処理に適用する。

詰まったら聞く。ここでは「何をすべきか」だけを Input/Output/なぜ で示す。
中身は自分で書く。

背景:
  - docs/notes/mcp-101-tutorial/01_why_and_what.md(MCPの全体像、システムダイヤグラム)
  - src/hello_mcp.py(同じMCPの型、@mcp.tool()の使い方)
  - src/hello_gemini.py(Geminiの基本的な呼び方、ただしテキストのみ。
    今回は画像/PDFを渡すマルチモーダル呼び出しが新しく必要になる)
  - src/load_receipts.py(このツールが出力するJSONを最終的に読み込む側。
    receipt_id / store / transaction / items のキー名はここと合わせること)

Called by: MCPクライアント(Claude Desktop/Claude Code)
Depends on: mcp, google-genai, python-dotenv
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp.server.fastmcp import FastMCP

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


# ============================================================
# システムプロンプト。今まで手動でGeminiに渡していたものをそのまま持ってくる。
# AI Studioの「オレンジのところ」に対応するのがこの定数
# (SDK上は system_instruction として渡す)。省略・要約せず、そのまま。
# ============================================================
SYSTEM_PROMPT = """あなたはドイツ生活の家計管理をサポートする優秀なデータエンジニアリングアシスタントです。
ユーザーから提供されるドイツのスーパー（Lidl、Kaufland、dm、go asiaなど）のレシート画像（PNG）またはPDFからデータを正確に抽出し、指定されたJSONフォーマットで出力してください。

【厳守するデータ処理ルール】
1. 為替レート: 常に「1 EUR = 184 JPY」で固定して計算し、小数点以下は切り捨て（整数）にしてください。
2. 割引の処理: 「Preisvorteil」や「Rabatt」などの割引がある場合、対象商品の discount_eur にマイナスの値（例: -0.20）を入力し、regular_eur + discount_eur = final_eur となるように計算してください。割引がない場合は discount_eur を 0.0 にしてください。
3. Pfand（デポジット）の処理:
   - 容器代の支払い（Pfand, Pfandartikelなど）は、category を "Pfand" にしてください。
   - 空き瓶の返却（Leergut, Pfandrückgabeなど）によるマイナス額は、category を "Pfand_Return" にしてください。
4. 翻訳とカテゴリ分類: ドイツ語の品目名 (name_original) から、自然な日本語名 (name_jp) を推測して入力してください。また、品目に応じて以下の category のいずれかを割り当ててください。
   [Food, Beverage, Snack, Daily_Necessities, Pfand, Pfand_Return, Discount]
5. 全体割引の処理: 買い物全体に対する割引（例: 5% Rabatt）がある場合は、品目リストの1つの独立したアイテムとして扱い、category を "Discount" にしてください。
6. 文字のデコード: "&amp;" のようなHTMLエンティティは、"&" のように元の記号にデコードしてから出力してください（"&amp;" をそのまま出力しないこと）。

【出力フォーマット】
以下のJSONスキーマに厳密に従い、余計な挨拶や説明は一切省いてJSONコードブロックのみを出力してください。

[
  {
    "receipt_id": "店舗名_YYYYMMDD_番号",
    "store": {
      "name": "店舗名",
      "address": "レシートに記載の住所"
    },
    "transaction": {
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "total_eur": 0.00,
      "exchange_rate_jpy": 184,
      "total_jpy": 0
    },
    "items": [
      {
        "name_original": "ドイツ語の品目名",
        "name_jp": "日本語の品目名",
        "category": "カテゴリ名",
        "price": {
          "regular_eur": 0.00,
          "discount_eur": 0.00,
          "final_eur": 0.00
        }
      }
    ]
  }
]"""


mcp = FastMCP("receipt-extractor")


def _extract_receipt_via_gemini(file_path: str) -> str:
    """レシートのPDF/画像ファイルを読み込み、Geminiに渡して構造化JSONを返してもらう。

    Input:
        file_path: レシートのPDFまたは画像(PNG)ファイルへのパス

    Output:
        str: SYSTEM_PROMPTのJSONスキーマに従ったJSON文字列(コードブロック無し)

    なぜ:
        hello_gemini.pyはテキストだけを渡すシンプルな例だったが、
        レシート処理では画像/PDFそのものをGeminiに渡す必要がある
        (マルチモーダル入力)。システムプロンプトの渡し方も、
        今回は正式に system_instruction として分離する。
    """
    # TODO 1: file_pathからバイト列を読み込む
    #   ヒント: Path(file_path).read_bytes()
    PATH = Path(file_path)
    data = PATH.read_bytes()
    

    # TODO 2: ファイルの種類(PDF/PNG)に応じてmime_typeを決める
    #   ヒント: file_path.lower().endswith(".pdf") なら "application/pdf"、
    #   そうでなければ "image/png"(必要なら.jpgなども後で足す)
    if file_path.lower().endswith(".pdf"):
        mime_type = "application/pdf"
    else:
        mime_type = "image/png"

    # TODO 3: Geminiにシステムプロンプト + ファイルを渡して呼び出す
    #   ヒント:
    #   client.models.generate_content(
    #       model=model_name,
    #       contents=[
    #           types.Part.from_bytes(data=読み込んだバイト列, mime_type=mime_type),
    #       ],
    #       config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    #   )
    #   前回話した通り、AI Studioの「オレンジのところ」が
    #   ここでいう system_instruction にそのまま対応する。
    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=data, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )

    # TODO 4: response.text を返す
    #   注意: Geminiが```json ... ```のようにコードブロック付きで返してくることがある。
    #   SYSTEM_PROMPTで「JSONコードブロックのみ」と指定済みだが、
    #   実際の出力を見てから、必要ならここで```json/```を取り除く処理を足す
    return response.text


@mcp.tool()
def extract_receipt(file_path: str) -> str:
    """レシートのPDF/画像ファイルを構造化JSONに変換するツール。

    Input:
        file_path: レシートのPDFまたは画像ファイルへの絶対パス

    Output:
        str: JSON文字列(店舗名・日付・品目ごとの価格・カテゴリなど、
             src/load_receipts.pyが読み込める形式)

    なぜ:
        今まで「PDF/画像を見ながら手動でGeminiに投げてJSONを貼り付ける」
        という作業を、MCP経由でLLMアプリから直接呼び出せるようにする。
        ファイルパスを渡すだけで済むようになる。
    """
    return _extract_receipt_via_gemini(file_path)


if __name__ == "__main__":
    # hello_mcp.pyと同じく、これ単体を実行しても画面には何も出ない
    # (MCPクライアントからの接続を待ち受ける状態になるだけ)。
    mcp.run()
