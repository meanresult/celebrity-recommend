import streamlit as st
from datetime import date, timedelta

from admin_service import DAG_CONFIGS, build_execution_plan, trigger_dag_runs
from domain import (
    build_account_post_details_query,
    DEFAULT_SELECTED_BRANDS,
    build_brand_accounts_query,
    build_data_freshness_query,
    build_header_context,
    build_brand_overall_query,
    build_first_tab_insight,
    build_top_brand_summary,
    extract_brand_options,
    format_data_freshness,
    prepare_accounts_table,
    prepare_top_accounts_snapshot,
    summarize_kpis,
)
from presentation import (
    configure_page,
    render_accounts_tab,
    render_empty_selection,
    render_footer,
    render_header,
    render_kpi_cards,
    render_admin_help,
    render_analysis_switch_header,
    render_overall_tab,
    render_sidebar,
)
from query_service import run_query


def main() -> None:
    configure_page()
    freshness_df = run_query(build_data_freshness_query())
    last_loaded_at, latest_post_date = format_data_freshness(freshness_df)

    brand_df = run_query(
        """
        SELECT DISTINCT tagged_account
        FROM fsh.mart.account_tagged_accounts
        ORDER BY tagged_account;
        """
    )
    brand_options = extract_brand_options(brand_df)
    selected_brands = render_sidebar(brand_options, DEFAULT_SELECTED_BRANDS)

    if not selected_brands:
        render_empty_selection()
        st.stop()

    render_header(build_header_context(selected_brands, last_loaded_at, latest_post_date))

    with st.spinner("데이터 불러오는 중..."):
        df_accounts = run_query(build_brand_accounts_query(selected_brands))
        df_overall = run_query(build_brand_overall_query(selected_brands))
        df_account_posts = run_query(build_account_post_details_query(selected_brands))

    render_kpi_cards(summarize_kpis(selected_brands, df_accounts, df_overall))

    render_analysis_switch_header()

    with st.expander("관리자 도구", expanded=False):
        render_admin_help()

        admin_brand_options = list(DAG_CONFIGS.keys())
        default_admin_brands = [admin_brand_options[0]] if admin_brand_options else []
        admin_selected_brands = st.multiselect(
            "실행할 브랜드",
            options=admin_brand_options,
            default=default_admin_brands,
            key="admin_selected_brands",
        )

        col1, col2 = st.columns(2)
        default_start = date.today() - timedelta(days=1)
        default_end = date.today()
        admin_start_date = col1.date_input("시작일(KST)", value=default_start, key="admin_start_date")
        admin_end_date = col2.date_input("종료일(KST)", value=default_end, key="admin_end_date")

        if admin_start_date > admin_end_date:
            st.error("시작일은 종료일보다 늦을 수 없습니다.")
        elif not admin_selected_brands:
            st.warning("최소 1개 이상의 브랜드를 선택해주세요.")
        else:
            plan_df = build_execution_plan(admin_selected_brands, admin_start_date, admin_end_date)
            st.markdown("**실행 계획 미리보기**")
            st.dataframe(plan_df, use_container_width=True, hide_index=True)

            total_runs = len(plan_df.index)
            st.caption(f"총 {total_runs}개의 DAG run이 생성됩니다.")

            if st.button("선택한 기간 실행", type="primary", key="trigger_selected_runs"):
                with st.spinner("Airflow DAG 실행 요청 중..."):
                    result_df = trigger_dag_runs(admin_selected_brands, admin_start_date, admin_end_date)
                st.session_state["admin_trigger_results"] = result_df

        if "admin_trigger_results" in st.session_state:
            st.markdown("**실행 결과**")
            st.dataframe(st.session_state["admin_trigger_results"], use_container_width=True, hide_index=True)

    tab1, tab2 = st.tabs(["공통 태그 계정", "함께 등장한 브랜드"])

    with tab1:
        render_accounts_tab(
            df_accounts,
            prepare_accounts_table(df_accounts),
            prepare_top_accounts_snapshot(df_accounts),
            build_first_tab_insight(df_accounts, df_overall),
            df_overall,
            df_account_posts,
        )

    with tab2:
        render_overall_tab(df_overall, build_top_brand_summary(df_overall))

    render_footer(last_loaded_at)


if __name__ == "__main__":
    main()
