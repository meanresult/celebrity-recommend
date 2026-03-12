from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


PALETTE = {
    "bg": "#08111f",
    "surface": "#0e1728",
    "surface_alt": "#152239",
    "border": "#273552",
    "text": "#f6f8fc",
    "muted": "#a5b1c8",
    "accent": "#c89a63",
    "accent_dark": "#a9783d",
    "ink_soft": "#d6deee",
    "chip": "#16243b",
    "success": "#7dd9a6",
    "warning": "#f5c56b",
    "danger": "#f08b7d",
}


def configure_page() -> None:
    st.set_page_config(
        page_title="Instagram 브랜드 분석",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable.css');

        :root {{
            --bg: {PALETTE["bg"]};
            --surface: {PALETTE["surface"]};
            --surface-alt: {PALETTE["surface_alt"]};
            --border: {PALETTE["border"]};
            --text: {PALETTE["text"]};
            --muted: {PALETTE["muted"]};
            --accent: {PALETTE["accent"]};
            --accent-dark: {PALETTE["accent_dark"]};
            --ink-soft: {PALETTE["ink_soft"]};
            --chip: {PALETTE["chip"]};
        }}

        html, body, [class*="css"] {{
            font-family: "Pretendard Variable", "Pretendard", sans-serif;
            color: var(--text);
        }}
        .stApp {{
            background:
                radial-gradient(circle at top right, rgba(200, 154, 99, 0.12), transparent 22%),
                radial-gradient(circle at top left, rgba(42, 82, 160, 0.14), transparent 18%),
                linear-gradient(180deg, #08111f 0%, #0a1324 100%);
        }}
        header[data-testid="stHeader"] {{
            background: transparent;
        }}
        [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {{
            display: none !important;
        }}
        .main .block-container {{
            padding-top: 2.2rem;
            padding-bottom: 2.5rem;
            max-width: 1480px;
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0c1424 0%, #10192c 100%);
            border-right: 1px solid rgba(143, 164, 204, 0.12);
        }}
        [data-testid="stSidebar"] * {{
            color: var(--text);
        }}
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {{
            background: #0a1120 !important;
            color: var(--text) !important;
            border: 1px solid rgba(143, 164, 204, 0.14) !important;
        }}
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="popover"] > div,
        [data-testid="stSidebar"] [data-baseweb="tag"] {{
            background: #0a1120 !important;
            color: var(--text) !important;
            border-color: rgba(143, 164, 204, 0.14) !important;
        }}
        [data-testid="stSidebar"] [data-baseweb="tag"] {{
            background: rgba(200,154,99,0.16) !important;
        }}
        .hero-card {{
            background: linear-gradient(145deg, rgba(14,23,40,0.94) 0%, rgba(21,34,57,0.92) 100%);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 1.55rem 1.65rem;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
            margin-bottom: 1.15rem;
        }}
        .hero-eyebrow {{
            color: var(--accent);
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }}
        .hero-title {{
            font-size: 2.25rem;
            line-height: 1.15;
            font-weight: 800;
            margin: 0 0 0.55rem 0;
        }}
        .hero-copy {{
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.6;
            margin: 0;
        }}
        .hero-meta {{
            margin-top: 1rem;
            color: var(--ink-soft);
            font-size: 0.94rem;
            font-weight: 600;
        }}
        .chip-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.8rem;
        }}
        .brand-chip {{
            display: inline-flex;
            align-items: center;
            padding: 0.38rem 0.7rem;
            border-radius: 999px;
            background: var(--chip);
            border: 1px solid rgba(200, 154, 99, 0.22);
            color: var(--text);
            font-size: 0.86rem;
            font-weight: 700;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.34rem 0.66rem;
            border-radius: 999px;
            font-size: 0.84rem;
            font-weight: 800;
            border: 1px solid transparent;
        }}
        .status-badge.healthy {{
            background: rgba(125, 217, 166, 0.12);
            color: {PALETTE["success"]};
            border-color: rgba(125, 217, 166, 0.22);
        }}
        .status-badge.watch {{
            background: rgba(245, 197, 107, 0.12);
            color: {PALETTE["warning"]};
            border-color: rgba(245, 197, 107, 0.22);
        }}
        .status-badge.stale {{
            background: rgba(240, 139, 125, 0.12);
            color: {PALETTE["danger"]};
            border-color: rgba(240, 139, 125, 0.22);
        }}
        .status-badge.neutral {{
            background: rgba(214, 222, 238, 0.08);
            color: var(--ink-soft);
            border-color: rgba(214, 222, 238, 0.14);
        }}
        .kpi-card {{
            background: rgba(14, 23, 40, 0.96);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.15rem 1.15rem 1rem 1.15rem;
            min-height: 144px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
        }}
        .kpi-label {{
            color: var(--muted);
            font-size: 0.88rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        .kpi-value {{
            color: var(--text);
            font-size: 2.05rem;
            line-height: 1.1;
            font-weight: 800;
            letter-spacing: -0.03em;
        }}
        .kpi-note {{
            color: var(--muted);
            font-size: 0.92rem;
            margin-top: 0.45rem;
            line-height: 1.45;
        }}
        .insight-card {{
            background: linear-gradient(135deg, rgba(200,154,99,0.12) 0%, rgba(45,71,110,0.18) 100%);
            border: 1px solid rgba(200, 154, 99, 0.2);
            border-radius: 20px;
            padding: 1rem 1.15rem;
            margin-bottom: 1rem;
        }}
        .insight-label {{
            color: var(--accent);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }}
        .insight-text {{
            color: var(--text);
            font-size: 1rem;
            line-height: 1.6;
            margin: 0;
        }}
        .section-card {{
            background: rgba(14, 23, 40, 0.96);
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.15rem 1.2rem;
            box-shadow: 0 14px 30px rgba(0, 0, 0, 0.18);
            height: 100%;
        }}
        .section-title {{
            font-size: 1.15rem;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 0.2rem;
        }}
        .section-subtitle {{
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.55;
            margin-bottom: 0.9rem;
        }}
        .tab-note {{
            color: var(--muted);
            font-size: 0.95rem;
            margin-top: -0.2rem;
            margin-bottom: 0.8rem;
        }}
        .account-rank-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.9rem 0;
            border-bottom: 1px solid rgba(143, 164, 204, 0.12);
        }}
        .account-rank-item:last-child {{
            border-bottom: none;
            padding-bottom: 0.15rem;
        }}
        .account-rank-left {{
            min-width: 0;
        }}
        .account-rank-name {{
            font-size: 1rem;
            font-weight: 700;
            color: var(--text);
            line-height: 1.35;
        }}
        .account-rank-id {{
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 0.15rem;
        }}
        .account-rank-stats {{
            text-align: right;
            white-space: nowrap;
        }}
        .account-rank-value {{
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--text);
        }}
        .account-rank-note {{
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 0.15rem;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.5rem;
            margin-bottom: 1.1rem;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: rgba(14,23,40,0.74);
            border: 1px solid rgba(143,164,204,0.16);
            border-radius: 999px;
            color: var(--muted);
            font-weight: 700;
            padding: 0.4rem 0.95rem;
        }}
        .stTabs [aria-selected="true"] {{
            background: rgba(200,154,99,0.14) !important;
            border-color: rgba(200,154,99,0.32) !important;
            color: var(--text) !important;
        }}
        .stButton > button {{
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            min-height: 42px;
            font-weight: 700;
            background: #ffffff;
            color: #08111f;
        }}
        .stButton > button * {{
            color: #08111f !important;
        }}
        .stButton > button:hover {{
            background: #eef2f8;
            color: #08111f;
            border-color: rgba(255, 255, 255, 0.2);
        }}
        .stButton > button[kind="primary"] {{
            background: #ffffff;
            color: #08111f;
            border: 1px solid rgba(255, 255, 255, 0.18);
        }}
        .stAlert {{
            background: rgba(14, 23, 40, 0.96);
            color: var(--text);
            border: 1px solid var(--border);
        }}
        [data-testid="stExpander"] {{
            background: rgba(14, 23, 40, 0.92);
            border: 1px solid var(--border);
            border-radius: 16px;
        }}
        [data-testid="stDataFrame"] {{
            background: rgba(14, 23, 40, 0.92);
            border: 1px solid var(--border);
            border-radius: 16px;
        }}
        .stMarkdown, .stText, .stCaption, p, label, h1, h2, h3, h4, h5, h6 {{
            color: var(--text);
        }}
        .action-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            margin: 1.1rem 0 0.75rem 0;
        }}
        .action-bar-title {{
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--text);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(context: dict[str, object]) -> None:
    selected_brands = context["selected_brands"]
    selected_brand_chips = "".join(
        f'<span class="brand-chip">{brand}</span>' for brand in selected_brands
    ) or '<span class="brand-chip">선택 없음</span>'
    status = context["status"]
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-eyebrow">Brand Co-tag Dashboard</div>
            <div class="hero-title">Instagram 취향 연결 분석</div>
            <p class="hero-copy">
                선택한 브랜드를 함께 태그한 계정과, 그 계정들이 또 어떤 브랜드를 함께 태그하는지
                한 화면에서 비교할 수 있도록 정리한 내부 분석 대시보드입니다.
            </p>
            <div class="chip-row">
                {selected_brand_chips}
                <span class="status-badge {status["tone"]}">{status["label"]}</span>
            </div>
            <div class="hero-meta">분석 기준: {context["analysis_rule"]}</div>
            <div class="hero-meta">마지막 적재 시각: {context["last_loaded_at"]} | 최신 게시물 기준일: {context["latest_post_date"]}</div>
            <div class="hero-meta" style="font-weight: 500; color: {PALETTE["muted"]};">{status["description"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(brand_options: list[str], default_selected: list[str]) -> list[str]:
    st.sidebar.subheader("필터 설정")

    valid_defaults = [brand for brand in default_selected if brand in brand_options]
    if "applied_brands" not in st.session_state:
        st.session_state["applied_brands"] = valid_defaults
    if "pending_brands" not in st.session_state:
        st.session_state["pending_brands"] = st.session_state["applied_brands"]

    search_query = st.sidebar.text_input(
        "브랜드 검색",
        value=st.session_state.get("brand_search", ""),
        placeholder="예: lemaire",
        key="brand_search",
    ).strip().lower()

    filtered_options = [
        brand for brand in brand_options if search_query in brand.lower()
    ] if search_query else brand_options

    visible_options = sorted(set(filtered_options) | set(st.session_state["pending_brands"]))

    st.sidebar.multiselect(
        "브랜드 선택",
        options=visible_options,
        default=st.session_state["pending_brands"],
        key="pending_brands",
        help="한 개 이상 선택하면 공통으로 태그한 계정만 추려서 분석합니다.",
    )

    col1, col2 = st.sidebar.columns(2)
    if col1.button("적용", use_container_width=True, type="primary"):
        st.session_state["applied_brands"] = st.session_state["pending_brands"]
    if col2.button("초기화", use_container_width=True):
        st.session_state["pending_brands"] = valid_defaults
        st.session_state["applied_brands"] = valid_defaults
        st.session_state["brand_search"] = ""
        st.rerun()

    if st.sidebar.button("데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    with st.sidebar.expander("도움말", expanded=False):
        st.caption(
            "선택한 브랜드를 모두 함께 태그한 계정만 추린 뒤, "
            "그 계정이 추가로 어떤 브랜드를 함께 태그했는지 비교합니다."
        )

    return st.session_state["applied_brands"]


def render_empty_selection() -> None:
    st.header("브랜드를 먼저 선택해주세요")
    st.markdown("왼쪽 필터에서 1개 이상의 브랜드를 선택하면, 공통 태그 계정과 함께 등장한 브랜드를 분석해 보여줍니다.")
    st.warning("왼쪽 사이드바에서 최소 1개 이상의 브랜드를 선택해주세요.")


def render_kpi_cards(kpis: list[dict[str, str]]) -> None:
    columns = st.columns(3)
    for column, metric in zip(columns, kpis):
        column.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{metric["label"]}</div>
                <div class="kpi-value">{metric["value"]}</div>
                <div class="kpi-note">{metric["note"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_accounts_tab(
    df_accounts_raw: pd.DataFrame,
    df_accounts_table: pd.DataFrame,
    df_accounts_snapshot: pd.DataFrame,
    insight_text: str,
    df_overall: pd.DataFrame,
    df_account_posts: pd.DataFrame,
) -> None:
    st.markdown(
        """
        <div class="insight-card">
            <div class="insight-label">핵심 인사이트</div>
            <p class="insight-text">"""
        + insight_text
        + """</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([1.1, 1], gap="large")

    with left_col:
        render_top_accounts_snapshot(df_accounts_snapshot)

    with right_col:
        render_brand_snapshot(df_overall)

    st.markdown("### 공통 태그 계정 상세")
    st.markdown(
        '<div class="tab-note">표에서 `상세 보기`를 눌러 계정별 게시물 수집 기준의 전체 태그 계정을 아래에서 확인할 수 있습니다.</div>',
        unsafe_allow_html=True,
    )

    if df_accounts_table.empty:
        st.markdown("선택한 브랜드를 태그한 계정이 없습니다.")
    else:
        render_accounts_table(df_accounts_table)
        render_account_brand_expanders(df_accounts_raw, df_account_posts)


def render_accounts_table(df_accounts_table: pd.DataFrame) -> None:
    table_df = df_accounts_table.copy()
    table_df.insert(0, "상세 보기", False)
    edited_df = st.data_editor(
        table_df,
        use_container_width=True,
        hide_index=True,
        key="accounts_detail_editor",
        disabled=[
            "작성자 아이디",
            "프로필 이름",
            "선택 브랜드 총 태그 수",
            "최근 게시물 날짜",
            "프로필 링크",
        ],
        column_config={
            "상세 보기": st.column_config.CheckboxColumn("상세 보기"),
            "프로필 링크": st.column_config.LinkColumn(
                "프로필 링크",
                display_text="열기",
            ),
        },
    )
    selected_rows = edited_df[edited_df["상세 보기"]]
    if selected_rows.empty:
        st.session_state["selected_account_detail_id"] = None
    else:
        st.session_state["selected_account_detail_id"] = selected_rows.iloc[-1]["작성자 아이디"]


def render_account_brand_expanders(df_accounts_raw: pd.DataFrame, df_account_posts: pd.DataFrame) -> None:
    if df_accounts_raw.empty:
        return

    st.markdown("### 계정별 전체 브랜드 보기")
    st.markdown(
        '<div class="tab-note">위 표에서 선택한 계정의 게시물별 태그 계정 목록을 보여줍니다.</div>',
        unsafe_allow_html=True,
    )

    selected_account_id = st.session_state.get("selected_account_detail_id")
    if not selected_account_id:
        st.info("공통 태그 계정 상세 표에서 `상세 보기`를 눌러 계정을 선택해주세요.")
        return

    selected_candidates = df_accounts_raw[df_accounts_raw["INSTA_ID"] == selected_account_id]
    if selected_candidates.empty:
        st.warning("선택한 계정 정보를 찾을 수 없습니다.")
        return

    selected_row = selected_candidates.iloc[0]

    insta_id = selected_row.get("INSTA_ID") or "unknown"
    insta_name = selected_row.get("INSTA_NAME") or "unknown"
    display_name = insta_name if insta_name != "unknown" else insta_id
    latest_date = selected_row.get("LATEST_RELATED_DATE") or "-"
    selected_tag_count = selected_row.get("SELECTED_BRAND_TAG_POST_COUNT") or 0
    total_tagged = selected_row.get("TOTAL_TAGGED_ACCOUNT_COUNT") or 0
    account_posts = df_account_posts[df_account_posts["INSTA_ID"] == insta_id].copy()
    account_posts["POST_DATE"] = account_posts["POST_DATE"].fillna("-")

    st.markdown(
        f"""
        <div class="section-card" style="margin-top: 0.5rem;">
            <div class="section-title">{display_name} (@{insta_id})</div>
            <div class="section-subtitle">최근 게시물 날짜 {latest_date} · 선택 브랜드 총 태그 {selected_tag_count}회 · 전체 태그 계정 {total_tagged}개</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"프로필 링크: [instagram.com/{insta_id}](https://www.instagram.com/{insta_id}/)")

    if account_posts.empty:
        st.info("이 계정의 게시물 상세 태그 데이터가 없습니다.")
        return

    for index, row in enumerate(account_posts.to_dict(orient="records"), start=1):
        post_date = row.get("POST_DATE") or "-"
        post_id = row.get("POST_ID") or "-"
        tagged_accounts = row.get("TAGGED_ACCOUNTS") or "-"
        full_link = row.get("FULL_LINK") or "-"
        st.markdown(f"**게시물 {index}** · {post_date} · `{post_id}`")
        if full_link != "-":
            st.markdown(f"원본 링크: [열기]({full_link})")
        st.code(str(tagged_accounts), language="text")


def render_top_accounts_snapshot(df_accounts: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">상위 공통 계정 랭킹</div>
            <div class="section-subtitle">선택한 브랜드를 실제로 몇 번 태그했는지 기준으로 높은 계정부터 보여줍니다.</div>
        """,
        unsafe_allow_html=True,
    )

    if df_accounts.empty:
        st.markdown("공통 계정 데이터가 없습니다.", unsafe_allow_html=False)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    html_items = []
    for _, row in df_accounts.iterrows():
        profile_name = row["프로필 이름"]
        account_id = row["작성자 아이디"]
        selected_tag_count = row["선택 브랜드 총 태그 수"]
        selected_tag_breakdown = row["선택 브랜드 태그 상세"]
        latest_date = row["최근 게시물 날짜"]
        html_items.append(
            f"""
            <div class="account-rank-item">
                <div class="account-rank-left">
                    <div class="account-rank-name">{profile_name}</div>
                    <div class="account-rank-id">@{account_id} · 최근 {latest_date}</div>
                </div>
                <div class="account-rank-stats">
                    <div class="account-rank-value">총 {selected_tag_count}회</div>
                    <div class="account-rank-note">{selected_tag_breakdown}</div>
                </div>
            </div>
            """
        )

    st.markdown("".join(html_items) + "</div>", unsafe_allow_html=True)


def render_brand_snapshot(df_overall: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">함께 등장한 브랜드 스냅샷</div>
            <div class="section-subtitle">선택한 브랜드를 태그한 계정들이, 어떤 다른 브랜드를 함께 태그했는지 계정당 1회 기준으로 집계한 상위 8개입니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df_overall.empty:
        st.markdown("함께 등장한 브랜드 데이터가 없습니다.")
        return

    chart_df = df_overall.head(8).copy()
    chart = px.bar(
        chart_df,
        x="ACCOUNT_COUNT",
        y="TAGGED_ACCOUNT",
        orientation="h",
        color_discrete_sequence=["#ffffff"],
        text="ACCOUNT_COUNT",
    )
    chart.update_traces(
        textposition="outside",
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>태그한 계정 수: %{x}<br>총 태그 횟수: %{customdata[0]}<extra></extra>",
        customdata=chart_df[["TAGGED_POST_TOTAL"]].to_numpy(),
    )
    chart.update_layout(
        height=420,
        margin={"l": 0, "r": 10, "t": 8, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Pretendard Variable, Pretendard, sans-serif", "color": PALETTE["text"]},
        xaxis_title="태그한 계정 수",
        yaxis_title="",
        yaxis={"categoryorder": "total ascending"},
        xaxis={"gridcolor": "rgba(143,164,204,0.16)", "zeroline": False},
        showlegend=False,
    )
    st.plotly_chart(chart, use_container_width=True)


def render_top_brand_chart(df_overall: pd.DataFrame) -> None:
    if df_overall.empty:
        return

    top_df = df_overall.head(10).copy()
    chart = px.bar(
        top_df,
        x="ACCOUNT_COUNT",
        y="TAGGED_ACCOUNT",
        orientation="h",
        color_discrete_sequence=["#ffffff"],
        labels={
            "ACCOUNT_COUNT": "태그한 계정 수",
            "TAGGED_ACCOUNT": "브랜드 계정",
            "TAGGED_POST_TOTAL": "총 태그 횟수",
        },
    )
    chart.update_layout(
        height=430,
        yaxis={"categoryorder": "total ascending"},
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Pretendard Variable, Pretendard, sans-serif", "color": PALETTE["text"]},
        showlegend=False,
    )
    chart.update_xaxes(gridcolor="rgba(143,164,204,0.16)", zeroline=False)
    chart.update_traces(
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>태그한 계정 수: %{x}<br>총 태그 횟수: %{customdata[0]}<extra></extra>",
        customdata=top_df[["TAGGED_POST_TOTAL"]].to_numpy(),
    )
    st.plotly_chart(chart, use_container_width=True)


def render_overall_tab(df_overall: pd.DataFrame, summary_text: str) -> None:
    st.header("선택한 브랜드와 함께 자주 등장한 브랜드")
    st.markdown(
        '<div class="tab-note">선택한 브랜드를 태그한 공통 계정들이, 추가로 어떤 브랜드를 함께 태그했는지 비교합니다.</div>',
        unsafe_allow_html=True,
    )

    if df_overall.empty:
        st.markdown("함께 등장한 브랜드 데이터가 없습니다.")
        return

    st.markdown(f"**상위 브랜드 요약**\n\n{summary_text}")
    render_top_brand_chart(df_overall)

    renamed = df_overall.rename(
        columns={
            "TAGGED_ACCOUNT": "브랜드 계정",
            "ACCOUNT_COUNT": "태그한 계정 수",
            "TAGGED_POST_TOTAL": "총 태그 횟수",
        }
    )
    st.dataframe(renamed, use_container_width=True, hide_index=True)


def render_footer(last_loaded_at: str) -> None:
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; color: {PALETTE["muted"]}; font-size: 0.92rem;'>
            Instagram tagged data dashboard | 마지막 적재 시각: {last_loaded_at}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_admin_help() -> None:
    st.header("관리자용 DAG 일괄 실행")
    st.markdown(
        '<div class="tab-note">여러 날짜를 한 번에 선택해 Airflow DAG를 생성합니다. 입력 날짜는 KST 기준이며, 시스템이 실행용 UTC logical_date로 자동 변환합니다.</div>',
        unsafe_allow_html=True,
    )
    st.info(
        "이 기능은 로컬 Docker 환경 기준입니다. 실행 전 airflow 컨테이너가 올라와 있어야 하며, 실행 결과는 아래 표에서 확인할 수 있습니다."
    )


def render_analysis_switch_header() -> None:
    st.markdown(
        """
        <div class="action-bar">
            <div class="action-bar-title">상세 분석</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
