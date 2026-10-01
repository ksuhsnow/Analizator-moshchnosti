import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Анализатор экспериментальной мощности",
    page_icon="⚗️",
    layout="wide",
)

# Лабораторная палитра
NAVY = "#173B57"
BLUE = "#2878A5"
TEAL = "#3B8C91"
LIGHT = "#F2F6F9"

st.markdown(
    """
    <style>
      .stApp { background: #F5F7FA; }
      .block-container { max-width: 1200px; padding-top: 2rem; }
      .hero {
        background: linear-gradient(110deg, #173B57, #28647D);
        color: white; padding: 25px 30px; border-radius: 12px;
        margin-bottom: 22px;
      }
      .hero h1 { color: white; margin: 0; font-size: 29px; }
      .hero p { color: #DCEAF1; margin: 8px 0 0; }
      .section-title {
        color: #173B57; font-size: 20px; font-weight: 700;
        border-bottom: 2px solid #DCE5EC; padding-bottom: 8px;
        margin: 18px 0 12px;
      }
      div[data-testid="stMetric"] {
        background: white; border: 1px solid #DCE5EC;
        padding: 13px 15px; border-radius: 10px;
      }
      .note { color: #536777; font-size: 13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>АНАЛИЗАТОР ЭКСПЕРИМЕНТАЛЬНОЙ МОЩНОСТИ</h1>
      <p>Лабораторная обработка измерений · сравнение с номинальными параметрами аппарата</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">1. Параметры режимов аппарата</div>', unsafe_allow_html=True)
st.caption("Изменяй номинальную мощность и энергию. Можно добавить или удалить режимы.")

if "modes" not in st.session_state:
    st.session_state.modes = pd.DataFrame(
        [
            {"Режим": "Режим 1", "Номинальная мощность, Вт": 5.01, "Энергия, Дж": 3.7},
            {"Режим": "Режим 2", "Номинальная мощность, Вт": 15.0, "Энергия, Дж": 11.1},
            {"Режим": "Режим 3", "Номинальная мощность, Вт": 25.0, "Энергия, Дж": 18.5},
        ]
    )

edited_modes = st.data_editor(
    st.session_state.modes,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Режим": st.column_config.TextColumn("Название режима", required=True),
        "Номинальная мощность, Вт": st.column_config.NumberColumn(
            "Номинальная мощность, Вт", min_value=0.000001, format="%.4f", required=True
        ),
        "Энергия, Дж": st.column_config.NumberColumn(
            "Энергия, Дж", min_value=0.0, format="%.4f"
        ),
    },
    key="mode_editor",
)
st.session_state.modes = edited_modes.copy()

st.markdown('<div class="section-title">2. Экспериментальные измерения</div>', unsafe_allow_html=True)
st.caption("Введи по одному экспериментальному значению мощности для каждой строки. Количество измерений можно менять.")

mode_names = edited_modes["Режим"].astype(str).tolist() if not edited_modes.empty else []
if not mode_names:
    st.warning("Добавь хотя бы один режим в таблицу выше.")
    st.stop()

if "measurements" not in st.session_state:
    st.session_state.measurements = pd.DataFrame(
        [
            {"Режим": "Режим 1", "Измерение 1, Вт": 4.7, "Измерение 2, Вт": 4.8, "Измерение 3, Вт": 4.9},
            {"Режим": "Режим 2", "Измерение 1, Вт": 15.09, "Измерение 2, Вт": 15.01, "Измерение 3, Вт": 14.8},
            {"Режим": "Режим 3", "Измерение 1, Вт": 24.7, "Измерение 2, Вт": 24.8, "Измерение 3, Вт": 24.9},
        ]
    )

# Синхронизируем строки с текущим списком режимов, сохраняя введённые значения
old = st.session_state.measurements.copy()
new_rows = []
for name in mode_names:
    matches = old[old["Режим"].astype(str) == name] if "Режим" in old.columns else pd.DataFrame()
    if not matches.empty:
        new_rows.append(matches.iloc[0].to_dict())
    else:
        new_rows.append({
            "Режим": name,
            "Измерение 1, Вт": None,
            "Измерение 2, Вт": None,
            "Измерение 3, Вт": None,
        })
measurements_default = pd.DataFrame(new_rows)

edited_measurements = st.data_editor(
    measurements_default,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Режим": st.column_config.SelectboxColumn("Режим", options=mode_names, required=True),
        "Измерение 1, Вт": st.column_config.NumberColumn("Измерение 1, Вт", format="%.4f"),
        "Измерение 2, Вт": st.column_config.NumberColumn("Измерение 2, Вт", format="%.4f"),
        "Измерение 3, Вт": st.column_config.NumberColumn("Измерение 3, Вт", format="%.4f"),
    },
    key="measurement_editor",
)
st.session_state.measurements = edited_measurements.copy()

st.markdown('<div class="section-title">3. Расчёт и результаты</div>', unsafe_allow_html=True)
col_a, col_b = st.columns([1, 3])
with col_a:
    calculate = st.button("Рассчитать результаты", type="primary", use_container_width=True)
with col_b:
    st.markdown(
        '<p class="note">Отклонение считается относительно номинальной мощности: '
        'δ = |Pэксп − Pном| / Pном × 100%. Соответствие = 100% − δ.</p>',
        unsafe_allow_html=True,
    )

if calculate:
    nominal_lookup = {
        str(row["Режим"]): float(row["Номинальная мощность, Вт"])
        for _, row in edited_modes.iterrows()
        if pd.notna(row["Номинальная мощность, Вт"])
        and float(row["Номинальная мощность, Вт"]) > 0
    }
    energy_lookup = {
        str(row["Режим"]): (
            float(row["Энергия, Дж"]) if pd.notna(row["Энергия, Дж"]) else None
        )
        for _, row in edited_modes.iterrows()
    }

    result_rows = []
    for _, row in edited_measurements.iterrows():
        mode = str(row["Режим"])
        if mode not in nominal_lookup:
            continue
        nominal = nominal_lookup[mode]
        for column in ["Измерение 1, Вт", "Измерение 2, Вт", "Измерение 3, Вт"]:
            value = row.get(column)
            if pd.notna(value):
                experimental = float(value)
                deviation = abs(experimental - nominal) / nominal * 100
                result_rows.append({
                    "Режим": mode,
                    "Номинальная мощность, Вт": nominal,
                    "Энергия, Дж": energy_lookup.get(mode),
                    "Измерение": column.replace(", Вт", ""),
                    "Экспериментальная мощность, Вт": experimental,
                    "Отклонение, %": deviation,
                    "Соответствие, %": 100 - deviation,
                })

    if not result_rows:
        st.warning("Заполни хотя бы одно экспериментальное значение.")
    else:
        results = pd.DataFrame(result_rows)
        st.session_state.last_results = results

if "last_results" in st.session_state:
    results = st.session_state.last_results

    # Убираем результаты режимов, которые могли быть удалены или переименованы
    current_names = set(mode_names)
    results = results[results["Режим"].isin(current_names)]

    if not results.empty:
        st.markdown("#### Таблица результатов")
        st.dataframe(
            results.style.format({
                "Номинальная мощность, Вт": "{:.3f}",
                "Энергия, Дж": "{:.3f}",
                "Экспериментальная мощность, Вт": "{:.3f}",
                "Отклонение, %": "{:.3f}",
                "Соответствие, %": "{:.3f}",
            }).background_gradient(subset=["Отклонение, %"], cmap="RdYlGn_r"),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Сводка по режимам")
        summary = (
            results.groupby("Режим", as_index=False)
            .agg(
                Количество_измерений=("Отклонение, %", "count"),
                Среднее_отклонение_проц=("Отклонение, %", "mean"),
                Среднее_соответствие_проц=("Соответствие, %", "mean"),
            )
        )
        summary = summary.rename(columns={
            "Количество_измерений": "Количество измерений",
            "Среднее_отклонение_проц": "Среднее отклонение, %",
            "Среднее_соответствие_проц": "Среднее соответствие, %",
        })
        st.dataframe(
            summary.style.format({
                "Среднее отклонение, %": "{:.3f}",
                "Среднее соответствие, %": "{:.3f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### График сравнения")
        fig = px.scatter(
            results,
            x="Измерение",
            y="Экспериментальная мощность, Вт",
            color="Режим",
            symbol="Режим",
            hover_data=["Номинальная мощность, Вт", "Отклонение, %"],
            title="Экспериментальная мощность по измерениям",
        )
        for mode, group in results.groupby("Режим"):
            nominal = float(group["Номинальная мощность, Вт"].iloc[0])
            fig.add_hline(
                y=nominal,
                line_dash="dash",
                annotation_text=f"{mode}: номинал {nominal:g} Вт",
                annotation_position="top left",
            )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis_title="Номер измерения",
            yaxis_title="Мощность, Вт",
            legend_title="Режим",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Excel-экспорт
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            edited_modes.to_excel(writer, sheet_name="Параметры аппарата", index=False)
            edited_measurements.to_excel(writer, sheet_name="Экспериментальные данные", index=False)
            results.to_excel(writer, sheet_name="Результаты", index=False)
            summary.to_excel(writer, sheet_name="Сводка", index=False)

        st.download_button(
            "Скачать результаты в Excel",
            data=buffer.getvalue(),
            file_name=f"результаты_эксперимента_{datetime.now():%Y%m%d_%H%M}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

st.markdown("---")
st.markdown(
    '<p class="note">Примечание: программа сравнивает экспериментальную мощность с введённой номинальной мощностью. '
    'Энергия (Дж) сохраняется как параметр режима и не участвует в расчёте отклонения.</p>',
    unsafe_allow_html=True,
)
