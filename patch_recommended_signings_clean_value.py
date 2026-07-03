from pathlib import Path

path = Path("app/pages/11_Recommended_Signings.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''    value_col = find_column(df, ["Transfer Value", "Value"])

    if value_col:
        df["Estimated Value £M"] = df[value_col].apply(parse_money_to_millions)
    else:
        df["Estimated Value £M"] = np.nan
''',
'''    if "Estimated Value Clean" in df.columns:
        df["Estimated Value £M"] = pd.to_numeric(df["Estimated Value Clean"], errors="coerce") / 1_000_000
    elif "Estimated Value Clean £M" in df.columns:
        df["Estimated Value £M"] = pd.to_numeric(df["Estimated Value Clean £M"], errors="coerce")
    else:
        value_col = find_column(df, ["Transfer Value", "Value"])

        if value_col:
            df["Estimated Value £M"] = df[value_col].apply(parse_money_to_millions)
        else:
            df["Estimated Value £M"] = np.nan
'''
)

text = text.replace(
'''            value_display = row.get(value_col, "") if value_col else ""
''',
'''            if "Estimated Value Clean" in row.index and pd.notna(row.get("Estimated Value Clean")):
                clean_value = int(row.get("Estimated Value Clean"))
                value_display = f"£{clean_value:,.0f}"
            else:
                value_display = row.get(value_col, "") if value_col else ""
'''
)

text = text.replace(
'''                    "Estimated Value": value_display,
                    "Estimated Value £M": row.get("Estimated Value £M", np.nan),
''',
'''                    "Estimated Value": value_display,
                    "Estimated Value Clean": row.get("Estimated Value Clean", np.nan),
                    "Estimated Value Clean £M": row.get("Estimated Value Clean £M", np.nan),
                    "Estimated Value Status": row.get("Estimated Value Status", ""),
                    "Estimated Value £M": row.get("Estimated Value £M", np.nan),
'''
)

text = text.replace(
'''            "Estimated Value",
            "Why Recommended",
''',
'''            "Estimated Value",
            "Estimated Value Clean",
            "Estimated Value Clean £M",
            "Estimated Value Status",
            "Why Recommended",
'''
)

path.write_text(text, encoding="utf-8")
print("Patched Recommended Signings to use clean estimated values.")
