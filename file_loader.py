# utils/file_loader.py

import pandas as pd
from typing import Tuple


def _read_csv_with_multiple_encodings(file) -> pd.DataFrame:
    """
    업로드된 파일 객체에 대해 여러 인코딩을 시도하면서 CSV를 읽는다.
    주로 사용되는 한국어 인코딩(cp949, euc-kr 등)을 포함.
    """
    encodings_to_try = ["utf-8", "utf-8-sig", "cp949", "euc-kr"]

    last_error = None
    for enc in encodings_to_try:
        try:
            # 매번 처음부터 읽게 하기 위해 포인터를 0으로 되돌림
            file.seek(0)
            df = pd.read_csv(file, encoding=enc)
            # 성공하면 바로 반환
            return df
        except UnicodeDecodeError as e:
            last_error = e
            continue

    # 여기까지 오면 전부 실패
    raise UnicodeDecodeError(
        "CSV",
        b"",
        0,
        1,
        f"지원하는 인코딩으로 CSV를 읽을 수 없습니다. 마지막 오류: {last_error}"
    )


def load_expense_csv(file) -> pd.DataFrame:
    """
    지출 CSV 파일을 읽어서:
    - 인코딩 자동 처리 (utf-8, utf-8-sig, cp949, euc-kr 순으로 시도)
    - 날짜 컬럼을 datetime으로 변환
    - 금액 컬럼을 숫자형으로 변환
    - 기본 컬럼 이름이 맞는지 확인

    기대 컬럼 예시:
    - 날짜: 'date' 또는 '날짜'
    - 내용: 'description' 또는 '내용', '메모'
    - 금액: 'amount' 또는 '금액'
    """
    # ✅ 인코딩 자동 처리 부분
    df = _read_csv_with_multiple_encodings(file)

    # 날짜 컬럼 찾기
    date_candidates = ["date", "날짜", "일자"]
    date_col = None
    for c in date_candidates:
        if c in df.columns:
            date_col = c
            break
    if date_col is None:
        raise ValueError(f"날짜 컬럼이 없습니다. 날짜 컬럼명을 다음 중 하나로 설정해 주세요: {date_candidates}")

    # 내용(설명) 컬럼 찾기
    desc_candidates = ["description", "내용", "메모"]
    desc_col = None
    for c in desc_candidates:
        if c in df.columns:
            desc_col = c
            break
    if desc_col is None:
        raise ValueError(f"지출 내용 컬럼이 없습니다. 내용 컬럼명을 다음 중 하나로 설정해 주세요: {desc_candidates}")

    # 금액 컬럼 찾기
    amount_candidates = ["amount", "금액"]
    amount_col = None
    for c in amount_candidates:
        if c in df.columns:
            amount_col = c
            break
    if amount_col is None:
        raise ValueError(f"금액 컬럼이 없습니다. 금액 컬럼명을 다음 중 하나로 설정해 주세요: {amount_candidates}")

    # 타입 변환
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce")

    # 날짜/금액 중 결측치 제거
    df = df.dropna(subset=[date_col, amount_col])

    # 후처리에서 쓰기 쉽도록 컬럼명을 통일
    df = df.rename(columns={
        date_col: "date",
        desc_col: "description",
        amount_col: "amount",
    })

    return df
