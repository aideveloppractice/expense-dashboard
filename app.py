import streamlit as st
import pandas as pd
from utils.file_loader import load_csv_file
from utils.category_mapper import apply_category_mapping
st.set_page_config(
    page_title="개인 지출 분석 대시보드",
    page_icon="💸",
    layout="wide",
)

def main():
    st.title("💸 개인 지출 분석 대시보드")
    st.caption("CSV 업로드 → 날짜 변환 → 키워드 기반 카테고리 자동 분류 → 월별/카테고리별 분석")
    # === 1. CSV 업로드 ===
    st.sidebar.header("1️⃣ 데이터 업로드")
    uploaded_file = st.sidebar.file_uploader(
        "지출 내역 CSV 파일을 업로드하세요",
        type=["csv"],
    )
    if uploaded_file is None:
        st.info("왼쪽 사이드바에서 CSV 파일을 업로드하면 분석이 시작됩니다.")
        return

    # CSV 로드 및 기본 전처리 (인코딩 처리 등)
    df = load_csv_file(uploaded_file)
    if df is None or df.empty:
        st.error("CSV를 불러오지 못했습니다. 파일 형식을 확인해 주세요.")
        return
    st.subheader("1. 원본 데이터 미리보기")
    st.dataframe(df.head())

    # === 2. 컬럼 매핑 설정 (날짜 / 금액 / 설명 컬럼 선택) ===
    st.sidebar.header("2️⃣ 컬럼 설정")
    columns = list(df.columns)

    # 간단한 자동 추론 (기본 값용)
    def guess_col(candidates):
        for c in columns:
            lc = str(c).lower()
            if any(keyword in lc for keyword in candidates):
                return c
        return columns[0]
    date_col = st.sidebar.selectbox(
        "날짜(Date) 컬럼",
        options=columns,
        index=columns.index(guess_col(["date", "날짜", "일자"])) if columns else 0,
    )
    amount_col = st.sidebar.selectbox(
        "금액(Amount) 컬럼",
        options=columns,
        index=columns.index(guess_col(["amount", "금액", "지출", "expense"])) if columns else 0,
    )
    desc_col = st.sidebar.selectbox(
        "내용/메모(Description) 컬럼",
        options=columns,
        index=columns.index(guess_col(["desc", "메모", "내용", "상세", "내역"])) if columns else 0,
    )

    # 날짜 파싱 옵션
    st.sidebar.header("3️⃣ 날짜 옵션")
    manual_format = st.sidebar.text_input(
        "날짜 포맷 (선택, 예: %Y-%m-%d). 비워두면 자동 감지",
        value="",
        help="pandas.to_datetime에 들어가는 format 문자열입니다. (예: 2024-01-05 → %Y-%m-%d)",
    )

    # === 3. 날짜 컬럼 datetime 변환 & 금액 numeric 변환 ===
    df_processed = df.copy()
    # 날짜 변환
    if manual_format.strip():
        df_processed["date"] = pd.to_datetime(
            df_processed[date_col],
            format=manual_format.strip(),
            errors="coerce",
        )
    else:
        df_processed["date"] = pd.to_datetime(
            df_processed[date_col],
            errors="coerce",
        )

    # 금액 변환
    df_processed["amount"] = pd.to_numeric(
        df_processed[amount_col],
        errors="coerce",
    )

    # 유효한 데이터만 사용
    df_processed = df_processed.dropna(subset=["date", "amount"])
    if df_processed.empty:
        st.error("날짜 또는 금액 컬럼 변환 후 남는 유효한 데이터가 없습니다. 컬럼 설정/포맷을 다시 확인해 주세요.")
        return

    # 월 단위 컬럼 생성
    df_processed["month"] = df_processed["date"].dt.to_period("M").dt.to_timestamp()

    # === 4. 카테고리 자동 분류 ===
    df_processed = apply_category_mapping(df_processed, desc_col=desc_col)
    st.subheader("2. 변환된 데이터 미리보기 (날짜/금액/카테고리)")
    st.dataframe(
        df_processed[[ "date", "month", "amount", desc_col, "category" ]].head()
    )
    # === 5. 집계 및 시각화 ===
    st.subheader("3. 요약 리포트")
    total_spent = df_processed["amount"].sum()
    monthly_stats = (
        df_processed.groupby("month")["amount"]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    category_stats = (
        df_processed.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )
    avg_monthly = monthly_stats["amount"].mean()
    top_category_row = category_stats.iloc[0] if not category_stats.empty else None
    col1, col2, col3 = st.columns(3)
    col1.metric("총 지출 금액", f"{total_spent:,.0f}")
    col2.metric("월 평균 지출", f"{avg_monthly:,.0f}")
    if top_category_row is not None:
        col3.metric(
            "가장 많이 쓴 카테고리",
            f"{top_category_row['category']} ({top_category_row['amount']:,.0f})",
        )
    else:
        col3.metric("가장 많이 쓴 카테고리", "데이터 없음")

    # --- 월별 지출 추이 ---
    st.markdown("### 3-1. 월별 총 지출 추이")
    st.line_chart(
        data=monthly_stats,
        x="month",
        y="amount",
    )

    # --- 카테고리별 지출 합계 ---
    st.markdown("### 3-2. 카테고리별 총 지출")
    st.bar_chart(
        data=category_stats,
        x="category",
        y="amount",
    )

    # --- 월별 × 카테고리별 피벗 테이블 ---
    st.markdown("### 3-3. 월별 × 카테고리별 지출 피벗 테이블")
    pivot = pd.pivot_table(
        df_processed,
        index="month",
        columns="category",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )
    st.dataframe(pivot.style.format("{:,.0f}"))
    with st.expander("📄 원본 + 전처리 데이터(전체) 보기"):
        st.dataframe(df_processed)

if __name__ == "__main__":
    main()