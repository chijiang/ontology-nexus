import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from datetime import datetime


cur_year = datetime.today().year
cur_month = datetime.today().month


class FilterConditions(BaseModel):
    geo_ops: Optional[List[Literal["AP", "NA", "EMEA"]]] = Field(
        default=[],
        description="geography operation List, Supports one or more of AP, NA, EMEA and can be empty.",
    )
    PX_Region: Optional[List[Literal["WE"]]] = Field(
        default=[], description="region List, Supports WE and can be empty."
    )
    country_name_ops: Optional[List[Literal["INDIA", "CANADA", "FRANCE"]]] = Field(
        default=[],
        description="country List, Supports one or more of INDIA, CANADA, FRANCE and can be empty.",
    )
    program: Optional[List[Literal["Standard Commercial", "Premier Support"]]] = Field(
        default=[],
        description="service type List, Supports one or more of Standard Commercial, Premier Support and can be empty.",
    )
    trans_servdelivery: Optional[List[Literal["ONS", "CRU", "CIN"]]] = Field(
        default=[],
        description="transport delivery method List, Supports one or more of ONS, CRU, CIN and can be empty.",
    )
    start_year: Optional[int] = Field(
        default=None, description="starting year of the data analysis"
    )
    start_month: Optional[int] = Field(
        default=1, description="starting month of the data analysis, default to 1"
    )
    end_year: Optional[int] = Field(
        default=cur_year, description="starting year of the data analysis"
    )
    end_month: Optional[int] = Field(
        default=cur_month, description="starting year of the data analysis"
    )


df_all = pd.read_csv("work_ticket_emulator/sample_data.csv")
# df_all = pd.read_csv('sample_data.csv')

date_col = "interview_end_month_ops"
analysis_dims = {
    "Survey": ["Survey_Medium", "language"],
    "Location": ["geo_ops", "PX_Region", "PX_Sub_Region", "country_name_ops"],
    "SOInformation": ["program", "trans_servdelivery"],
    "Product": ["product_group_ops", "brand_ops"],
}
feature_cols = [
    "interview_end_month_ops",
    "Survey_Medium",
    "language",
    "geo_ops",
    "PX_Region",
    "PX_Sub_Region",
    "country_name_ops",
    "program",
    "trans_servdelivery",
    "product_group_ops",
    "brand_ops",
]


def filter_data(conditions=None):
    # by month; groupBy not supported
    df_filtered = df_all.copy()

    if conditions is None or len(conditions) == 0:
        return df_filtered

    start_year = conditions.pop("start_year") if "start_year" in conditions else None
    start_month = conditions.pop("start_month") if "start_month" in conditions else None
    end_year = conditions.pop("end_year") if "end_year" in conditions else None
    end_month = conditions.pop("end_month") if "end_month" in conditions else None

    # filter by conditions
    if conditions and len(conditions) > 0:
        mask = pd.Series([True] * len(df_all), index=df_all.index)

        for col, values in conditions.items():
            if col not in df_all.columns:
                raise ValueError(f"列名 '{col}' 不存在于DataFrame中")
            mask = mask & df_all[col].isin(values)

        df_filtered = df_all[mask]

    # filter by given time period
    df_filtered["end_date_dt"] = pd.to_datetime(df_filtered[date_col], format="%Y-%m")
    mask = pd.Series([True] * len(df_filtered), index=df_filtered.index)
    if start_year is not None:
        start_month = start_month if start_month is not None else 1
        if not 1 <= start_month <= 12:
            raise ValueError(f"起始月份{start_month}不合法，必须是1-12之间的整数")
        start_date = pd.to_datetime(f"{start_year}-{start_month:02d}", format="%Y-%m")
        mask = mask & (df_filtered["end_date_dt"] >= start_date)

    if end_year is not None:
        end_month = end_month if end_month is not None else 12
        if not 1 <= end_month <= 12:
            raise ValueError(f"结束月份{end_month}不合法，必须是1-12之间的整数")
        end_date = pd.to_datetime(f"{end_year}-{end_month:02d}", format="%Y-%m")
        mask = mask & (df_filtered["end_date_dt"] <= end_date)

    result_df = df_filtered[mask].drop(columns=["end_date_dt"]).reset_index(drop=True)

    return result_df


def calculate_t3B(df: pd.DataFrame):
    # t3b for each month
    df["OSAT"] = df["OSAT"].apply(lambda x: int(x))
    osat_result = (
        df.groupby(date_col)["OSAT"]
        .apply(lambda x: (x >= 8).mean())
        .reset_index(name="OSAT")
    )
    osat_result["OSAT(%)"] = osat_result["OSAT"].apply(lambda x: f"{x:.1%}")
    return osat_result


def calculate_contribution(df: pd.DataFrame):
    # categorical features & OSAT
    df["OSAT"] = df["OSAT"].apply(lambda x: int(x))
    cat_imputer = SimpleImputer(strategy="most_frequent")
    df[feature_cols] = pd.DataFrame(
        cat_imputer.fit_transform(df[feature_cols]),
        columns=feature_cols,
        index=df.index,
    )

    X, y = df[feature_cols], df[["OSAT"]]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(
                    sparse_output=False, drop="first", handle_unknown="ignore"
                ),
                feature_cols,
            )
        ],
        remainder="passthrough",
    )

    model_pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("scaler", StandardScaler()),
            ("lr", LinearRegression()),
        ]
    )

    model_pipeline.fit(X_train, y_train)
    overall_r2 = r2_score(y_test, model_pipeline.predict(X_test))
    print(f"整体模型解释度（R²）：{overall_r2:.4f}")

    # feature  importance
    feature_names = preprocessor.get_feature_names_out(feature_cols)
    lr_coef = model_pipeline.named_steps["lr"].coef_
    feature_importance = np.abs(lr_coef)

    # ratio
    total_importance = np.sum(feature_importance)
    feature_importance_ratio = (feature_importance / total_importance) * 100

    importance_df = pd.DataFrame(
        {
            "特征名称": feature_names,
            "标准化系数": lr_coef.flatten(),
            "特征重要性（绝对值）": feature_importance.flatten(),
            "重要性比重（%）": feature_importance_ratio.flatten(),
        }
    ).sort_values("特征重要性（绝对值）", ascending=False)

    # ---------------------- aggregate to original features ----------------------
    def aggregate_to_original_feature(importance_df, original_features):
        agg_result = []
        total_importance = np.sum(importance_df["特征重要性（绝对值）"])
        for col in original_features:
            sub_features = importance_df[
                importance_df["特征名称"].str.startswith(f"cat__{col}_")
            ]
            total_imp = sub_features["特征重要性（绝对值）"].sum()
            total_ratio = (total_imp / total_importance) * 100
            agg_result.append(
                {
                    "原始类别列": col,
                    "总特征重要性": round(total_imp, 4),
                    "总重要性比重（%）": round(total_ratio, 2),
                }
            )
        return pd.DataFrame(agg_result).sort_values("总特征重要性", ascending=False)

    original_imp_df = aggregate_to_original_feature(importance_df, feature_cols)

    # ---------------------- aggregate on given dimensions ----------------------
    def aggregate_to_dimension(importance_df, dimensions):
        agg_result = []
        for col, fea_group in dimensions.items():
            sub_features = importance_df[importance_df["原始类别列"].isin(fea_group)]
            total_imp = sub_features["总重要性比重（%）"].sum()
            agg_result.append({"维度": col, "总重要性比重（%）": round(total_imp, 2)})
        return pd.DataFrame(agg_result).sort_values(
            "总重要性比重（%）", ascending=False
        )

    dim_imp = aggregate_to_dimension(original_imp_df, analysis_dims)

    return overall_r2, dim_imp


def t3b_pipeline(conditions=None):
    filtered_data = filter_data(conditions)
    if filtered_data.empty:
        raise ValueError(
            "Filter conditions resulted in empty dataset. Please adjust the filters."
        )
    df_t3b = calculate_t3B(filtered_data)
    r2, dim_importance = calculate_contribution(filtered_data)
    return (
        dict(zip(df_t3b[date_col], df_t3b["OSAT(%)"])),
        r2,
        dict(zip(dim_importance["维度"], dim_importance["总重要性比重（%）"])),
    )


if __name__ == "__main__":
    conditions = {
        "country_name_ops": ["INDIA"],
        "trans_servdelivery": ["CIN", "ONS"],
        "start_year": 2025,
        "start_month": 10,
        "end_year": 2025,
    }
    df_t3b, r2, dim_importance = t3b_pipeline(conditions)
    print(df_t3b)
    print(r2)
    print(dim_importance)
