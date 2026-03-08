#!/usr/bin/env python3
"""간단한 운영 대시보드 (Streamlit)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "result" / "g2b_history.db"


def fetch_runs(limit: int = 30):
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT run_id, run_ts, year, total_count, disc_count, const_count, serv_count, quality_level
            FROM run_history
            ORDER BY run_ts DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return rows


def fetch_top_categories(run_id: str, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT category, COUNT(*) AS n
            FROM plan_items
            WHERE run_id = ?
            GROUP BY category
            ORDER BY n DESC
            LIMIT ?
            """,
            (run_id, limit),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return rows


def run_streamlit():
    import streamlit as st

    st.set_page_config(page_title="G2B Dashboard", layout="wide")
    st.title("G2B 운영 대시보드")

    runs = fetch_runs(50)
    if not runs:
        st.warning("이력 DB가 없습니다. 먼저 collect.py를 실행해 주세요.")
        return

    st.subheader("최근 실행 이력")
    st.dataframe(
        [
            {
                "run_id": r[0],
                "run_ts": r[1],
                "year": r[2],
                "total_count": r[3],
                "disc_count": r[4],
                "const_count": r[5],
                "serv_count": r[6],
                "quality": r[7],
            }
            for r in runs
        ],
        use_container_width=True,
    )

    run_ids = [r[0] for r in runs]
    selected = st.selectbox("상세 보기 run_id", run_ids, index=0)

    st.subheader("업종 Top 10")
    top = fetch_top_categories(selected, 10)
    st.dataframe(
        [{"category": c, "count": n} for c, n in top],
        use_container_width=True,
    )

    st.caption(f"DB: {DB_PATH}")


def run_cli_fallback():
    runs = fetch_runs(5)
    if not runs:
        print("이력 DB가 없습니다. 먼저 collect.py를 실행하세요.")
        return
    print("최근 실행 5건")
    for row in runs:
        print(
            f"- {row[1]} | run_id={row[0]} | year={row[2]} | total={row[3]} | "
            f"disc={row[4]} | quality={row[7]}"
        )
    print("\nStreamlit이 있으면 아래로 실행하세요:")
    print("  py -m streamlit run dashboard.py")


if __name__ == "__main__":
    try:
        import streamlit  # noqa: F401
        run_streamlit()
    except Exception:
        run_cli_fallback()
