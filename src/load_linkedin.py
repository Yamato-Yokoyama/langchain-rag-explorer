"""
src/load_linkedin.py

LinkedIn export(Shares.csv / Connections.csv)を Document のリストに変換する Loader。
他の loader(src/load_receipts.py)と同じインターフェース(list[Document])で
rag_pipeline に統合しやすくする。
"""
import re
from datetime import datetime

import pandas as pd
from langchain_core.documents import Document

_QUOTED_NEWLINE_PATTERN = re.compile(r'"\n"')
_PAREN_PATTERN = re.compile(r"\([^)]*\)")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:@[\w-]+)?\.[\w.-]+")


def load_shares_from_csv(filepath: str) -> list[Document]:
    """LinkedIn Shares export CSV を Document のリストに変換する。

    Input:
        filepath: str - Shares_XXXXX.csv の相対 or 絶対パス

    Output:
        list[Document] - 投稿ごとに Document 1 個
                         空 commentary の行は除外

    なぜ:
        - load_receipts と同じインターフェース(list[Document])で build_index に統合
        - 空 commentary = 単純リシェア、本文検索の対象外
    """
    df = pd.read_csv(filepath)

    docs = []
    for _, row in df.iterrows():
        commentary = row.get("ShareCommentary")
        if pd.isna(commentary) or not str(commentary).strip():
            continue

        page_content = _clean_share_commentary(str(commentary))

        date_clean = _parse_share_date(row.get("Date"))
        media_url = row.get("MediaUrl")
        has_media = pd.notna(media_url) and str(media_url).strip() != ""

        metadata = {
            "source": filepath,
            "date": date_clean,
            "year_month": date_clean[:7] if date_clean else None,
            "share_url": row.get("ShareLink"),
            "has_media": bool(has_media),
            "visibility": row.get("Visibility"),
            "char_length": len(page_content),
        }

        docs.append(Document(page_content=page_content, metadata=metadata))

    return docs


def load_connections_from_csv(filepath: str) -> list[Document]:
    """LinkedIn Connections export CSV を Document のリストに変換する。

    Input:
        filepath: str - Connections.csv の相対 or 絶対パス

    Output:
        list[Document] - コネクションごとに Document 1 個
                         個人情報保護のためイニシャル化 + email/URL drop
                         Company が空の行は除外

    なぜ:
        - 第三者情報のため、GDPR/DSGVO 観点で生データは load しない
        - Company + Position + 日付だけで「どんな繋がりを持ってきたか」の意味は残せる
        - イニシャル化で Yamato 自身の記憶想起も可能に保つ
    """
    # LinkedIn export の先頭 3 行は preamble(説明文)、実データは4行目からヘッダ
    df = pd.read_csv(filepath, skiprows=3)

    docs = []
    for _, row in df.iterrows():
        company = row.get("Company")
        if pd.isna(company) or not str(company).strip():
            continue

        initials = _initials(row.get("First Name"), row.get("Last Name"))
        position = row.get("Position")
        position_text = str(position).strip() if pd.notna(position) and str(position).strip() else "unknown position"
        connected_on = _parse_connection_date(row.get("Connected On"))

        # Company / Position 欄に組織の SNS ハンドル等がメールっぽい形で
        # 混入しているケースがあるため、page_content 生成時に除去する
        company_display = _EMAIL_PATTERN.sub("", str(company)).strip()
        position_display = _EMAIL_PATTERN.sub("", position_text).strip()

        page_content = f"{initials}, {position_display} at {company_display} (connected on {connected_on})."

        metadata = {
            "source": filepath,
            "initials": initials,
            "company": company,
            "position": position if pd.notna(position) else None,
            "connected_on": connected_on,
            "year_month": connected_on[:7] if connected_on else None,
        }

        docs.append(Document(page_content=page_content, metadata=metadata))

    return docs


def _initials(first: str, last: str) -> str:
    """フルネームからイニシャル(例: 'C.M.')を生成。

    - 'Chuan Meng' → 'C.M.'
    - 'Kunihiro (Kuni)' 括弧内は無視 → 'K.I.'
    - 名前が空 or 1 単語のみは '?.?.' で index 統一性を保つ
    """
    def _clean(name) -> str:
        if not isinstance(name, str):
            return ""
        return _PAREN_PATTERN.sub("", name).strip()

    first_clean = _clean(first)
    last_clean = _clean(last)

    if not first_clean or not last_clean:
        return "?.?."

    return f"{first_clean[0].upper()}.{last_clean[0].upper()}."


def _clean_share_commentary(text: str) -> str:
    """ShareCommentary に混入している '"\\n"' 型の citation quote artifact を除去する。

    元データは改行のたびに前後を '"' で囲む形でエスケープされており
    (例: '...Izakaya🇯🇵"\\n"ドイツに来て...'）、単純な strip では取り切れない。
    """
    cleaned = _QUOTED_NEWLINE_PATTERN.sub("\n", text)
    return cleaned.strip('"').strip()


def _parse_share_date(raw: str) -> str | None:
    """Shares の Date 列 ('2026-07-28 20:32:32') を 'YYYY-MM-DD' に変換する。"""
    if not isinstance(raw, str) or not raw.strip():
        return None
    return datetime.fromisoformat(raw).date().isoformat()


def _parse_connection_date(raw: str) -> str | None:
    """Connections の Connected On 列 ('12 Aug 2026') を 'YYYY-MM-DD' に変換する。"""
    if not isinstance(raw, str) or not raw.strip():
        return None
    return datetime.strptime(raw, "%d %b %Y").date().isoformat()


if __name__ == "__main__":
    shares = load_shares_from_csv("data/linkedin/Shares_929332257.csv")
    print(f"Shares loaded: {len(shares)}")
    print("Sample:", shares[0])
    print("---")
    conns = load_connections_from_csv("data/linkedin/Connections.csv")
    print(f"Connections loaded: {len(conns)}")
    print("Sample:", conns[0])
    # Privacy assert
    # 単純な "@" not in text だと "GTM @ ElevenLabs" のような役職表記の
    # at 記号を誤検知するため、メールアドレスらしきパターンでのみ判定する
    for doc in conns:
        assert not _EMAIL_PATTERN.search(doc.page_content), f"Email leaked! {doc.page_content!r}"
        assert "linkedin.com/in/" not in doc.page_content, "URL leaked!"
    print("Privacy assertions passed.")
