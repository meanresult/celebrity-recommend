import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# ============================================================================
# 페이지 설정
# ============================================================================
st.set_page_config(
    page_title="Instagram 브랜드 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 커스텀 스타일
# ============================================================================
st.markdown("""
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
""", unsafe_allow_html=True)

# ============================================================================
# Snowflake 연결
# ============================================================================
def get_snowflake_connection():
    """Snowflake DB 연결 객체(conn) 생성"""
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def _execute_query(query: str) -> pd.DataFrame:
    """쿼리 실행 (캐시 없이 실제 실행 담당)"""
    conn = None
    cur = None
    try:
        conn = get_snowflake_connection()
        cur = conn.cursor()
        cur.execute(query)  # ✅ execute 오타 주의
        return cur.fetch_pandas_all()

    except Exception as e:
        st.error(f"❌ 쿼리 실행 실패: {e}")
        return pd.DataFrame()

    finally:
        try:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()
        except Exception:
            pass

@st.cache_data(ttl=600)  # 10분 캐시
def run_query(query: str) -> pd.DataFrame:
    return _execute_query(query)


# ============================================================================
# 헤더
# ============================================================================
st.title("📊 Instagram 브랜드 태그 분석 대시보드")
st.markdown("---")

# ============================================================================
# 사이드바 - 필터
# ============================================================================
# 브랜드 리스트 불러오기
brand_all = run_query(f"""
          SELECT DISTINCT tagged_account
          FROM fsh.stage.group_by_tagged_post
          ORDER BY tagged_account;
        
          """)

list_of_brands = brand_all['TAGGED_ACCOUNT'].tolist()

st.sidebar.header("🔍 필터 설정")

# 브랜드 선택
all_brands = list_of_brands
selected_brands = st.sidebar.multiselect(
    "브랜드 선택",
    options=all_brands,
    default=['amomento.co', 'lemaire']
)

# 데이터 새로고침 버튼
if st.sidebar.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("💡 왼쪽에서 브랜드를 선택하고 분석 결과를 확인하세요!")

# ============================================================================
# 메인 콘텐츠
# ============================================================================

if not selected_brands:
    st.header("브랜드 태그 분석")
    st.markdown("선택한 브랜드를 태그한 계정들이 함께 태그한 태그한 현황을 분석합니다.")
    st.markdown("")
    st.warning("⚠️ 왼쪽 사이드바에서 최소 1개 이상의 브랜드를 선택해주세요!")
    st.stop()

# 탭 생성
tab1,tab2= st.tabs(["📈 태그 분석","🙋🏻‍♂️계정 분석"])

# ----------------------------------------------------------------------------
# TAB 1: 브랜드 태그 분석 - 계정 
# ----------------------------------------------------------------------------
# 선택한 브랜드를 태그한 계정들을 보여줍니다 

with tab1:
    st.header("나와 비슷한 취향의 사람들은 누가 있을까?")
    st.markdown("선택한 브랜드를 공통으로 태그한 계정들을 보여줍니다.")
    
    # SQL 쿼리 - 선택한 브랜드를 태그한 계정들
    conditions = [
        f"brands_tagged LIKE '%{selected_brand}%'" 
        for selected_brand in selected_brands
        ]

    where_clause = " AND ".join(conditions)

    query_accounts = f"""
        SELECT
            insta_id,
            brand_count,
            brands_tagged,
        FROM fsh.stage.cross_brand_accounts
        WHERE {where_clause}
        ORDER BY insta_id DESC;
        """
    
    with st.spinner('데이터 불러오는 중...'): # 데이터 로딩 스피너
        df_accounts = run_query(query_accounts)
    
    if df_accounts.empty:
        st.markdown("선택한 브랜드를 태그한 계정이 없습니다.")
    else:
        st.dataframe(df_accounts, use_container_width=True)   

# ----------------------------------------------------------------------------
# TAB 2: 계정분석
# ----------------------------------------------------------------------------
with tab2:
    st.header("나와 비슷한 취향의 사람들은 또 어떤 브랜드를 좋아할까?")
    st.markdown("당신과 유사한 취향을 가진 사람들이 태그한 브랜드 계정들을 보여줍니다")
    st.markdown("\n")
    st.markdown("\n")
    

    
    # SQL 쿼리 - 브랜드 선택한 사람들의 다른 브랜드 태그 현황 
    conditions = [
        f"brands_tagged LIKE '%{selected_brand}%'" 
        for selected_brand in selected_brands
        ]

    where_clause = " AND ".join(conditions)

    query_overall = f"""
        -- 1. 선택한 브랜드를 태그한 계정들
        WITH selected_brand_accounts AS (
            SELECT
                insta_id,
                -- brand_count,
                -- brands_tagged
            FROM fsh.stage.cross_brand_accounts
            WHERE {where_clause}
        ), 
        -- 2. 선택한 브랜드를 태그한 계정들이 태그한 다른 브랜드들
        brand_list as (
            SELECT DISTINCT
                insta_id,
                tagged_account
            FROM fsh.stage.group_by_tagged_post
            GROUP BY insta_id, tagged_account
        ),
        -- 3. 최종 결과 집계
        result AS(
            SELECT 
                b.tagged_account AS TAGGED_ACCOUNT,
                COUNT(DISTINCT b.insta_id) AS UNIQUE_ACCOUNTS,
                COUNT(*) AS TOTAL_POSTS
            FROM brand_list b
            INNER JOIN selected_brand_accounts s
            ON b.insta_id = s.insta_id
            GROUP BY b.tagged_account
        )
        SELECT *
        FROM result
        where TAGGED_ACCOUNT NOT IN ('{"', '".join(selected_brands)}')
        ORDER BY unique_accounts DESC, total_posts DESC;
        """
    
    with st.spinner('데이터 불러오는 중...'): # 데이터 로딩 스피너
        df_overall = run_query(query_overall)
    
    if df_overall.empty:
        brand_name_list = "해당 브랜드와 같이 태그된 브랜드가 없습니다."
    else:
        top_n = min(10, len(df_overall))  # ✅ 최대 10개, 적으면 적은대로
        lines = []
        for i in range(top_n):
            brand_name = df_overall["TAGGED_ACCOUNT"].iloc[i]
            lines.append(f"{i+1}. {brand_name} (태그 한 계정 수: {df_overall['UNIQUE_ACCOUNTS'].iloc[i]:,})")
        brand_name_list = "\n".join(lines)
        st.markdown(f"**선택한 브랜드와 함께 태그된 상위 {top_n}개 계정:**\n{brand_name_list}")   




# ============================================================================
# 푸터
# ============================================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Made with ❤️ using Streamlit | Data updated: {}
    </div>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M')),
    unsafe_allow_html=True
)