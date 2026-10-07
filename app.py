

import difflib
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# Page setup

st.set_page_config(page_title="Incidents Dashboard", page_icon="📊", layout="wide")

DATA_FILE = Path(__file__).parent / "incidents_updated.csv"
UNKNOWN = "Unknown"
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def show(fig):
    """Display a plotly figure full-width (works on old and new Streamlit)."""
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def show_df(data, **kwargs):
    """Display a dataframe full-width (works on old and new Streamlit)."""
    try:
        st.dataframe(data, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(data, use_container_width=True, **kwargs)



# State cleaning
# The State column is taken from the end of the Title, so it contains typos,

STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno",
    "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "FCT", "Gombe", "Imo",
    "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos",
    "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto",
    "Taraba", "Yobe", "Zamfara",
]

# Typos and place names that clearly belong to one state
ALIASES = {
    "abuja": "FCT", "fc t": "FCT", "fct abuja": "FCT", "abuja fct": "FCT",
    "akwa ibom offshore": "Akwa Ibom", "uyo": "Akwa Ibom",
    "anmabra": "Anambra",
    "bayelsa offshore": "Bayelsa",
    "bornon": "Borno", "gwoza": "Borno",
    "guma": "Benue",
    "cross rivers": "Cross River",
    "jiagawa": "Jigawa", "jigaawa": "Jigawa", "jigiwa": "Jigawa",
    "kadauna": "Kaduna", "kadun": "Kaduna",
    "katisna": "Katsina", "katstina": "Katsina",
    "nasaraawa": "Nasarawa", "nasarwa": "Nasarawa", "nassarawa": "Nasarawa",
    "niger state": "Niger",
    "river": "Rivers", "rivers offshore": "Rivers", "port harcourt": "Rivers", "bonny": "Rivers",
    "tabara": "Taraba",
    "zamafara": "Zamfara", "zamafra": "Zamfara",
    "badagry": "Lagos",
}

_SEARCH_KEYS = sorted(set([s.lower() for s in STATES] + list(ALIASES.keys())), key=len, reverse=True)
_SEARCH_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in _SEARCH_KEYS) + r")\b")


def _lookup(key):
    if key in ALIASES:
        return ALIASES[key]
    for s in STATES:
        if s.lower() == key:
            return s
    return None


def clean_state(raw, title=""):
    """Turn a messy state string (or, failing that, the whole title) into a state name."""
    for text in (raw, title):
        if not isinstance(text, str):
            continue
        key = re.sub(r"[^a-z ]", " ", text.lower())      # drop digits, brackets, quotes
        key = re.sub(r"\s+", " ", key).strip()
        if not key or key == "nigeria":                   # "Nigeria" is not a state
            continue
        hit = _lookup(key)
        if hit:
            return hit
        match = _SEARCH_RE.search(key)                    # e.g. "banditry katsina 1"
        if match:
            return _lookup(match.group(1))
        if text is raw and " " not in key and len(key) >= 5:   # last resort: close spelling
            close = difflib.get_close_matches(key, [s.lower() for s in STATES], n=1, cutoff=0.82)
            if close:
                return _lookup(close[0])
    return UNKNOWN


# ----------------------------------------------------------------------------
# Load + prepare data (same steps as the notebook)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Preparing data...")
def prepare(raw: pd.DataFrame):
    df = raw.copy()
    n_raw = len(df)

    df["Start date"] = pd.to_datetime(df["Start date"], errors="coerce")
    df["End date"] = pd.to_datetime(df["End date"], errors="coerce")
    df["Number of deaths"] = pd.to_numeric(df["Number of deaths"], errors="coerce").fillna(0).astype(int)

    df = df.drop_duplicates()
    n_dupes = n_raw - len(df)

    n_before = len(df)
    df = df.dropna(subset=["Start date"])
    n_bad_dates = n_before - len(df)

    df["Year"] = df["Start date"].dt.year.astype(int)
    df["Month"] = df["Start date"].dt.month
    df["Month Name"] = df["Start date"].dt.month_name()
    df["Quarter"] = df["Start date"].dt.quarter
    df["Day of Week"] = df["Start date"].dt.day_name()

    state_raw = df["Title"].str.split(",").str[-1].str.strip()
    df["State"] = [clean_state(s, t) for s, t in zip(state_raw, df["Title"])]
    df["Cause"] = df["Title"].str.rsplit(",", n=1).str[0].str.strip()

    return df.reset_index(drop=True), n_dupes, n_bad_dates


def load_raw():
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE)
    st.warning(f"`{DATA_FILE.name}` was not found next to app.py. Upload it below.")
    uploaded = st.file_uploader("Upload incidents CSV", type="csv")
    if uploaded is None:
        st.stop()
    return pd.read_csv(uploaded)


raw_df = load_raw()
missing = {"Title", "Start date", "Number of deaths"} - set(raw_df.columns)
if missing:
    st.error(f"The CSV is missing these columns: {', '.join(sorted(missing))}")
    st.stop()

df, n_dupes, n_bad_dates = prepare(raw_df)

# ----------------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")

min_year, max_year = int(df["Year"].min()), int(df["Year"].max())
if min_year == max_year:
    year_range = (min_year, max_year)
    st.sidebar.write(f"Year: {min_year}")
else:
    year_range = st.sidebar.slider("Year range", min_year, max_year, (min_year, max_year))

all_states = sorted(s for s in df["State"].unique() if s != UNKNOWN)
if (df["State"] == UNKNOWN).any():
    all_states.append(UNKNOWN)
selected_states = st.sidebar.multiselect(
    "State (leave empty for all)", all_states, default=[],
    help="Pick one or more states. Empty means every state.",
)

mask = df["Year"].between(*year_range)
if selected_states:
    mask &= df["State"].isin(selected_states)
fdf = df[mask]

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Data cleaning: {n_dupes:,} duplicate rows removed, "
    f"{n_bad_dates:,} rows with invalid dates dropped."
)

# ----------------------------------------------------------------------------
# Header + KPIs
# ----------------------------------------------------------------------------
st.title("📊 Incidents Dashboard")
st.caption("Interactive view of incident records. Use the filters on the left.")

if fdf.empty:
    st.warning("No data matches the current filters. Widen the year range or clear the state filter.")
    st.stop()

known = fdf[fdf["State"] != UNKNOWN]
total_incidents = len(fdf)
total_deaths = int(fdf["Number of deaths"].sum())
avg_deaths = total_deaths / total_incidents
max_single = int(fdf["Number of deaths"].max())

inc_by_year = fdf.groupby("Year").size()
peak_year = int(inc_by_year.idxmax())

if known.empty:
    top_state_label, top_state_value = "n/a", ""
else:
    top_state = known["State"].value_counts()
    top_state_label, top_state_value = top_state.idxmax(), f"{top_state.max():,} incidents"

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total incidents", f"{total_incidents:,}")
k2.metric("Total deaths", f"{total_deaths:,}")
k3.metric("Avg deaths / incident", f"{avg_deaths:.1f}")
k4.metric("Deadliest single incident", f"{max_single:,}")
k5.metric("Peak year (incidents)", f"{peak_year}", f"{inc_by_year.max():,} incidents", delta_color="off")
k6.metric("Top state", top_state_label, top_state_value, delta_color="off")

st.markdown("")

tab_trend, tab_state, tab_death, tab_more, tab_data = st.tabs(
    ["📈 Incident trend", "🗺️ State analysis", "💀 Death analysis", "🔎 Causes & patterns", "📋 Data & download"]
)

# ----------------------------------------------------------------------------
# Tab 1: Incident trend
# ----------------------------------------------------------------------------
with tab_trend:
    c1, c2 = st.columns(2)

    with c1:
        by_year = fdf.groupby("Year").size().reset_index(name="Incidents")
        fig = px.bar(by_year, x="Year", y="Incidents", text="Incidents", title="Incidents per year")
        fig.update_xaxes(type="category")
        fig.update_traces(marker_color="#6C4AB6", textposition="outside")
        show(fig)

    with c2:
        monthly = (
            fdf.set_index("Start date").resample("MS").size().reset_index(name="Incidents")
        )
        fig = px.line(monthly, x="Start date", y="Incidents", title="Monthly incident trend", markers=True)
        fig.update_traces(line_color="#6C4AB6")
        fig.update_layout(xaxis_title="Month")
        show(fig)

    by_month = (
        fdf.groupby("Month Name").size().reindex(MONTH_ORDER).fillna(0).reset_index(name="Incidents")
    )
    by_month.columns = ["Month", "Incidents"]
    fig = px.bar(by_month, x="Month", y="Incidents", title="Incidents by calendar month (all selected years)")
    fig.update_traces(marker_color="#9B7FD4")
    show(fig)

# ----------------------------------------------------------------------------
# Tab 2: State analysis
# ----------------------------------------------------------------------------
with tab_state:
    n_unknown = int((fdf["State"] == UNKNOWN).sum())
    if known.empty:
        st.info("No incidents with an identifiable state in the current selection.")
    else:
        top_n = st.slider("Number of states to show", 3, 37, 10)
        state_tbl = (
            known.groupby("State")
            .agg(Incidents=("Identifier", "size"), Deaths=("Number of deaths", "sum"))
            .reset_index()
        )
        state_tbl["Deaths per incident"] = (state_tbl["Deaths"] / state_tbl["Incidents"]).round(2)

        c1, c2 = st.columns(2)
        with c1:
            top_inc = state_tbl.sort_values("Incidents", ascending=False).head(top_n)
            fig = px.bar(top_inc.sort_values("Incidents"), x="Incidents", y="State", orientation="h",
                         title=f"Top {top_n} states by incidents")
            fig.update_traces(marker_color="#6C4AB6")
            show(fig)
        with c2:
            fig = px.scatter(state_tbl, x="Incidents", y="Deaths", size="Deaths", hover_name="State",
                             text="State", title="Incidents vs deaths by state")
            fig.update_traces(textposition="top center", marker_color="#6C4AB6")
            show(fig)

        st.subheader("State summary")
        show_df(state_tbl.sort_values("Incidents", ascending=False).reset_index(drop=True))

        if n_unknown:
            st.caption(f"{n_unknown:,} incident(s) have no identifiable state and are left out of these charts.")

# ----------------------------------------------------------------------------
# Tab 3: Death analysis
# ----------------------------------------------------------------------------
with tab_death:
    c1, c2 = st.columns(2)

    with c1:
        deaths_year = fdf.groupby("Year")["Number of deaths"].sum().reset_index(name="Deaths")
        fig = px.line(deaths_year, x="Year", y="Deaths", markers=True, title="Total deaths per year")
        fig.update_xaxes(type="category")
        fig.update_traces(line_color="#C0392B")
        show(fig)

    with c2:
        if known.empty:
            st.info("No identifiable states to chart.")
        else:
            deaths_state = (
                known.groupby("State")["Number of deaths"].sum().sort_values(ascending=False).head(10)
                .sort_values().reset_index(name="Deaths")
            )
            fig = px.bar(deaths_state, x="Deaths", y="State", orientation="h",
                         title="Top 10 states by deaths")
            fig.update_traces(marker_color="#C0392B")
            show(fig)

    c3, c4 = st.columns(2)
    with c3:
        fig = px.histogram(fdf, x="Number of deaths", nbins=40, log_y=True,
                           title="Deaths per incident (log scale)")
        fig.update_traces(marker_color="#C0392B")
        show(fig)

    with c4:
        top10_sum = fdf["Number of deaths"].nlargest(10).sum()
        share = top10_sum / total_deaths * 100 if total_deaths else 0
        same_year = "Yes" if int(deaths_year.loc[deaths_year["Deaths"].idxmax(), "Year"]) == peak_year else "No"
        st.markdown("#### Quick findings")
        st.write(f"- The 10 deadliest incidents account for **{share:.1f}%** of all deaths.")
        st.write(f"- Median deaths per incident: **{fdf['Number of deaths'].median():.0f}**.")
        st.write(
            f"- Year with most deaths: **{int(deaths_year.loc[deaths_year['Deaths'].idxmax(), 'Year'])}**. "
            f"Is it also the year with the most incidents? **{same_year}**."
        )

    st.subheader("10 deadliest incidents")
    deadliest = fdf.nlargest(10, "Number of deaths")[
        ["Identifier", "Title", "Start date", "State", "Number of deaths"]
    ].copy()
    deadliest["Start date"] = deadliest["Start date"].dt.date
    show_df(deadliest.reset_index(drop=True))

# ----------------------------------------------------------------------------
# Tab 4: Additional visualisations
# ----------------------------------------------------------------------------
with tab_more:
    c1, c2 = st.columns(2)

    with c1:
        metric = st.radio("Rank causes by", ["Deaths", "Incidents"], horizontal=True)
        cause_tbl = (
            fdf.groupby("Cause")
            .agg(Incidents=("Identifier", "size"), Deaths=("Number of deaths", "sum"))
            .reset_index()
        )
        top_causes = cause_tbl.sort_values(metric, ascending=False).head(15).sort_values(metric)
        fig = px.bar(top_causes, x=metric, y="Cause", orientation="h", title=f"Top 15 causes by {metric.lower()}")
        fig.update_traces(marker_color="#2E86C1")
        show(fig)

    with c2:
        st.write("")
        st.write("")
        dow = (
            fdf.groupby("Day of Week")
            .agg(Incidents=("Identifier", "size"), Deaths=("Number of deaths", "sum"))
            .reindex(DAY_ORDER)
            .reset_index()
        )
        fig = px.bar(dow, x="Day of Week", y="Incidents", title="Incidents by day of the week")
        fig.update_traces(marker_color="#2E86C1")
        show(fig)

    heat = fdf.pivot_table(index="Year", columns="Month Name", values="Identifier", aggfunc="count", fill_value=0)
    heat = heat.reindex(columns=[m for m in MONTH_ORDER if m in heat.columns])
    fig = px.imshow(heat, aspect="auto", color_continuous_scale="Purples",
                    labels=dict(color="Incidents"), title="Incidents heatmap: year x month")
    show(fig)


# Tab 5: Filtered data + download
# ----------------------------------------------------------------------------
with tab_data:
    st.write(f"Showing **{len(fdf):,}** records for years {year_range[0]} to {year_range[1]}"
             + (f" in {', '.join(selected_states)}." if selected_states else " in all states."))

    search = st.text_input("Search in title", placeholder="e.g. Boko Haram, Flooding, Auto Crash")
    table = fdf
    if search:
        table = table[table["Title"].str.contains(search, case=False, na=False)]

    cols = ["Identifier", "Title", "State", "Cause", "Start date", "End date", "Number of deaths",
            "Year", "Month Name", "Day of Week"]
    table = table[cols].sort_values("Start date", ascending=False)
    show_df(table.reset_index(drop=True), hide_index=True)

    st.download_button(
        "⬇️ Download filtered data (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="incidents_filtered.csv",
        mime="text/csv",
    )
