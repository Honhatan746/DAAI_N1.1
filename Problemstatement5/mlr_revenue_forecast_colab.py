"""Monthly ecommerce revenue forecast with Multiple Linear Regression (Colab-ready).

Input CSV: export monthly or transaction-level data with a date column and a
revenue column. For this project's cube, use DIM_DATE.full_date and
FACT_SALES_RETURN.net_amount (Net Amount measure), preferably joined at the
transaction level. The script aggregates transaction rows by month.

Google Colab: upload the CSV when prompted, then run this file/cell. Outputs
are saved as mlr_monthly_forecast.csv and mlr_test_predictions.csv.
"""

from pathlib import Path
import math

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


# --------------------------- USER SETTINGS ---------------------------
CSV_PATH = ""  # e.g. "/content/revenue.csv"; leave blank to upload in Colab
DATE_COLUMN = "full_date"  # alternative: order_date, date, order_date_key
REVENUE_COLUMN = "net_amount"  # cube's Net Amount measure
FORECAST_MONTHS = 6  # six future calendar months
TEST_MONTHS = 6  # six observed calendar months reserved for evaluation
# --------------------------------------------------------------------


def load_csv():
    path = CSV_PATH.strip()
    if path and Path(path).exists():
        return pd.read_csv(path)
    try:
        from google.colab import files  # type: ignore
        uploaded = files.upload()
        if not uploaded:
            raise ValueError("Chưa tải lên file CSV.")
        name = next(iter(uploaded))
        return pd.read_csv(name)
    except ImportError as exc:
        raise FileNotFoundError(
            "Hãy đặt CSV_PATH tới file dữ liệu hoặc chạy trên Google Colab để tải file lên."
        ) from exc


def resolve_column(df, requested, candidates):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for name in [requested, *candidates]:
        if name and name.strip().lower() in lookup:
            return lookup[name.strip().lower()]
    raise ValueError(
        f"Không tìm thấy cột '{requested}'. Các cột hiện có: {list(df.columns)}"
    )


def parse_dates(series):
    # Support DIM_DATE.full_date, SQL date, and YYYYMMDD date keys.
    if pd.api.types.is_numeric_dtype(series):
        vals = series.dropna()
        if len(vals) and vals.between(19000101, 21001231).all():
            return pd.to_datetime(series.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
    return pd.to_datetime(series, errors="coerce")


def make_monthly_series(df):
    date_col = resolve_column(
        df, DATE_COLUMN,
        ["full_date", "order_date", "date", "order_date_key", "forecast_date", "month"],
    )
    revenue_col = resolve_column(
        df, REVENUE_COLUMN,
        ["net_amount", "Net Amount", "revenue", "actual_revenue", "sales", "total_revenue"],
    )
    data = df[[date_col, revenue_col]].copy()
    data["date"] = parse_dates(data[date_col])
    data["revenue"] = pd.to_numeric(data[revenue_col], errors="coerce")
    data = data.dropna(subset=["date", "revenue"])
    if data.empty:
        raise ValueError("Không còn dòng dữ liệu ngày/doanh thu hợp lệ sau khi làm sạch.")
    data["month"] = data["date"].dt.to_period("M").dt.to_timestamp()
    # Sum transaction values to reproduce the cube's additive Net Amount measure.
    monthly = data.groupby("month")["revenue"].sum().sort_index()
    idx = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
    return monthly.reindex(idx, fill_value=0.0).astype(float).rename("revenue")


def feature_row(date, history, origin):
    """Features use only information available before the date being predicted."""
    t = (date.year - origin.year) * 12 + date.month - origin.month
    row = {
        "trend_month": float(t),
        "month_sin": math.sin(2 * math.pi * date.month / 12),
        "month_cos": math.cos(2 * math.pi * date.month / 12),
    }
    for lag in (1, 2, 3, 6, 12):
        row[f"lag_{lag}"] = float(history[-lag]) if len(history) >= lag else np.nan
    for window in (3, 6, 12):
        row[f"rolling_mean_{window}"] = (
            float(np.mean(history[-window:])) if len(history) >= window else np.nan
        )
    return row


def build_training_data(series, origin):
    rows, target, dates = [], [], []
    values = series.to_numpy(dtype=float)
    for i in range(len(values)):
        rows.append(feature_row(series.index[i], values[:i].tolist(), origin))
        target.append(values[i])
        dates.append(series.index[i])
    X = pd.DataFrame(rows, index=dates)
    valid = X.notna().all(axis=1)
    return X.loc[valid], pd.Series(target, index=dates).loc[valid]


def metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    denominator = np.abs(actual).sum()
    wape = np.abs(actual - predicted).sum() / denominator if denominator else np.nan
    return {
        "MAE": mean_absolute_error(actual, predicted),
        "RMSE": np.sqrt(mean_squared_error(actual, predicted)),
        "WAPE": wape,
    }


def main():
    df = load_csv()
    monthly = make_monthly_series(df)
    # A complete 12-month lag needs at least 13 training months to create
    # one training row, in addition to all six holdout months.
    min_months = 13 + TEST_MONTHS
    if len(monthly) < min_months:
        raise ValueError(
            f"Chỉ có {len(monthly)} tháng dữ liệu. Với holdout {TEST_MONTHS} tháng và lag 12 tháng, "
            f"cần tối thiểu {min_months} tháng liên tục. Hãy dùng toàn bộ lịch sử giao dịch."
        )
    test_n = TEST_MONTHS
    split = len(monthly) - test_n
    origin = monthly.index[0]

    # Chronological holdout; no random shuffling to avoid future leakage.
    train_series = monthly.iloc[:split]
    X_train, y_train = build_training_data(train_series, origin)
    if len(X_train) < 1:
        raise ValueError("Không đủ lịch sử để tạo đặc trưng lag cho huấn luyện.")
    model = LinearRegression()
    model.fit(X_train, y_train)

    history = monthly.iloc[:split].to_list()
    test_dates = monthly.index[split:]
    predictions = []
    for date in test_dates:
        X_next = pd.DataFrame([feature_row(date, history, origin)]).reindex(columns=X_train.columns)
        pred = float(model.predict(X_next)[0])
        predictions.append(pred)
        history.append(pred)  # recursive one-step forecast across holdout period

    evaluation = pd.DataFrame({
        "month": test_dates,
        "actual_revenue": monthly.iloc[split:].to_numpy(),
        "predicted_revenue": predictions,
    })
    score = metrics(evaluation.actual_revenue, evaluation.predicted_revenue)
    print("\n=== ĐÁNH GIÁ MLR TRÊN TẬP TEST THEO THỜI GIAN ===")
    print(f"Số tháng kiểm tra: {len(evaluation)}")
    print(f"MAE : {score['MAE']:,.2f}")
    print(f"RMSE: {score['RMSE']:,.2f}")
    print(f"WAPE: {score['WAPE']:.2%}" if np.isfinite(score["WAPE"]) else "WAPE: không xác định (tổng actual = 0)")
    print("\nDự báo tập test:")
    print(evaluation.to_string(index=False, formatters={
        "actual_revenue": "{:,.2f}".format,
        "predicted_revenue": "{:,.2f}".format,
    }))

    # Refit using all observed months, then forecast future months recursively.
    X_all, y_all = build_training_data(monthly, origin)
    final_model = LinearRegression().fit(X_all, y_all)
    history = monthly.to_list()
    future_dates = pd.date_range(monthly.index[-1] + pd.offsets.MonthBegin(1), periods=FORECAST_MONTHS, freq="MS")
    future_values = []
    for date in future_dates:
        X_next = pd.DataFrame([feature_row(date, history, origin)]).reindex(columns=X_all.columns)
        pred = float(final_model.predict(X_next)[0])
        future_values.append(pred)
        history.append(pred)
    future = pd.DataFrame({"month": future_dates, "forecast_revenue": future_values})
    # Guard against accidentally exporting daily dates: every output must be
    # exactly one row per distinct month, represented by its first calendar day.
    for label, output in (("holdout", evaluation), ("forecast", future)):
        dates = pd.to_datetime(output["month"])
        if dates.dt.day.ne(1).any() or dates.dt.to_period("M").duplicated().any():
            raise RuntimeError(f"Đầu ra {label} không phải một dòng duy nhất cho mỗi tháng.")
    if len(future) != FORECAST_MONTHS or len(evaluation) != TEST_MONTHS:
        raise RuntimeError("Số tháng đầu ra không khớp cấu hình 6 tháng.")
    evaluation.to_csv("mlr_test_predictions.csv", index=False)
    future.to_csv("mlr_monthly_forecast.csv", index=False)
    print("\n=== DỰ BÁO DOANH THU TƯƠNG LAI ===")
    print(future.to_string(index=False, formatters={"forecast_revenue": "{:,.2f}".format}))
    print("\nĐã lưu: mlr_test_predictions.csv, mlr_monthly_forecast.csv")
    try:
        from google.colab import files  # type: ignore
        files.download("mlr_monthly_forecast.csv")
        files.download("mlr_test_predictions.csv")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
