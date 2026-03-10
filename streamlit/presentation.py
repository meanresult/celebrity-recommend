from __future__ import annotations

from datetime import datetime

import streamlit as st


def configure_page() -> None:
    st.set_page_config(
        page_title="Instagram 브랜드 분석",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .main {
            padding-top: 2rem;
        }
        .stMetric {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.title("📊 Instagram 브랜드 태그 분석 대시보드")
    st.markdown("---")


def render_sidebar(brand_options: list[str], default_selected: list[str]) -> list[str]:
    st.sidebar.header("🔍 필터 설정")

    valid_defaults = [brand for brand in default_selected if brand in brand_options]
    selected_brands = st.sidebar.multiselect(
        "브랜드 선택",
        options=brand_options,
        default=valid_defaults,
    )

    if st.sidebar.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.info("💡 왼쪽에서 브랜드를 선택하고 분석 결과를 확인하세요!")
    return selected_brands


def render_empty_selection() -> None:
    st.header("브랜드 태그 분석")
    st.markdown("선택한 브랜드를 태그한 계정들이 함께 태그한 현황을 분석합니다.")
    st.warning("⚠️ 왼쪽 사이드바에서 최소 1개 이상의 브랜드를 선택해주세요!")


def render_accounts_tab(df_accounts) -> None:
    st.header("나와 비슷한 취향의 사람들은 누가 있을까?")
    st.markdown("선택한 브랜드를 공통으로 태그한 계정들을 보여줍니다.")

    if df_accounts.empty:
        st.markdown("선택한 브랜드를 태그한 계정이 없습니다.")
    else:
        st.dataframe(df_accounts, use_container_width=True)


def render_overall_tab(summary_text: str) -> None:
    st.header("나와 비슷한 취향의 사람들은 또 어떤 브랜드를 좋아할까?")
    st.markdown("당신과 유사한 취향을 가진 사람들이 태그한 브랜드 계정들을 보여줍니다")
    st.markdown(f"**선택한 브랜드와 함께 태그된 상위 브랜드:**\n{summary_text}")


def render_footer() -> None:
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            Made with ❤️ using Streamlit | Data updated: {}
        </div>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M")),
        unsafe_allow_html=True,
    )
