import streamlit as st

from domain import (
    DEFAULT_SELECTED_BRANDS,
    build_brand_accounts_query,
    build_brand_overall_query,
    build_top_brand_summary,
    extract_brand_options,
)
from presentation import (
    configure_page,
    render_accounts_tab,
    render_empty_selection,
    render_footer,
    render_header,
    render_overall_tab,
    render_sidebar,
)
from query_service import run_query


def main() -> None:
    configure_page()
    render_header()

    brand_df = run_query(
        """
        SELECT DISTINCT tagged_account
        FROM fsh.stage.group_by_tagged_post
        ORDER BY tagged_account;
        """
    )
    brand_options = extract_brand_options(brand_df)
    selected_brands = render_sidebar(brand_options, DEFAULT_SELECTED_BRANDS)

    if not selected_brands:
        render_empty_selection()
        st.stop()

    tab1, tab2 = st.tabs(["📈 태그 분석", "🙋🏻‍♂️계정 분석"])

    with tab1:
        with st.spinner("데이터 불러오는 중..."):
            df_accounts = run_query(build_brand_accounts_query(selected_brands))
        render_accounts_tab(df_accounts)

    with tab2:
        with st.spinner("데이터 불러오는 중..."):
            df_overall = run_query(build_brand_overall_query(selected_brands))
        render_overall_tab(build_top_brand_summary(df_overall))

    render_footer()


if __name__ == "__main__":
    main()
