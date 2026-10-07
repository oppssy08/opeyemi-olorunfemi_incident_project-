# Nigeria Incidents Dashboard

An interactive Streamlit dashboard that I built to analyse recorded incidents in Nigeria: road crashes, banditry, flooding, insurgency-related clashes and more. I started with a Jupyter notebook analysis and then turned it into a dashboard anyone can explore with filters, charts and a downloadable table.

> **Live app:** _add your Streamlit link here after deploying_
> **Author:** Opeyemi

---

## 1. Why I built this

I wanted to move beyond answering questions in a notebook and present the results in a form that a non-technical person can use. A dashboard lets someone pick a year or a state and immediately see how incidents and deaths change, without reading any code.

The questions I set out to answer:

1. How many incidents occurred each year, and which year had the most?
2. Which months record the most incidents?
3. Which states record the most incidents, and which are in the top 5?
4. What is the total number of deaths, and which states record the most?
5. Which individual incidents were the deadliest?
6. Does the year with the most incidents also have the most deaths?
7. What other patterns appear (causes, days of the week, concentration of deaths)?

## 2. The dataset

The data is a CSV file (`incidents_updated.csv`) with **10,978 records** and 5 columns:

| Column | Meaning |
|---|---|
| `Identifier` | Unique incident ID (e.g. `IBD031681`) |
| `Title` | Short description with the location at the end (e.g. `Auto Crash, Lagos`) |
| `Start date` | Date the incident began |
| `End date` | Date the incident ended |
| `Number of deaths` | Deaths recorded for the incident |

There were no missing values in the raw file, but there were other problems (see the next section).

## 3. How I went about it

### Step 1: Explore the data
I loaded the file with pandas and checked its shape, column types, missing values and duplicates using `head()`, `info()`, `isna().sum()`, `duplicated().sum()` and `describe()`.

### Step 2: Clean the data
- Converted `Start date` and `End date` from text to real dates with `pd.to_datetime`.
- Found **210 duplicate rows** and removed them with `drop_duplicates()`.
- Created new columns from the start date: **Year, Month, Month Name, Quarter, Day of Week**.

### Step 3: Extract State and Cause from the Title
There was no State column, but every title ends with the location, so I split the `Title` at the last comma:

```python
df["State"] = df["Title"].str.split(",").str[-1].str.strip()
df["Cause"] = df["Title"].str.rsplit(",", n=1).str[0]
```

### Step 4: Fix the messy State values
This was the hardest part. The extracted State column had **119 different values** when Nigeria only has 36 states plus the FCT. I found typos and inconsistencies such as `Bornon`, `Katisna`, `ANambra`, `Zamafra`, `River`, lower-case names like `kaduna`, extra words like `Banditry Katsina`, numbers like `Kano 2`, and places that are not states (`Badagry`, `Uyo`, `Port Harcourt`).

For the dashboard I wrote a `clean_state()` function that:
1. Lower-cases the text and removes digits and symbols.
2. Checks for an exact state name or a known alias (for example `Abuja` becomes `FCT`).
3. Searches for a state name inside longer text (for example `Banditry Katsina` becomes `Katsina`).
4. Falls back to a close-spelling match for typos.
5. Labels anything it cannot place as `Unknown`, so I never guess wrongly.

### Step 5: Analyse
I answered each question with pandas `groupby`, `value_counts` and `sort_values`, and drew charts with matplotlib and seaborn in the notebook.

### Step 6: Build the dashboard
I rebuilt the analysis as a Streamlit app (`app.py`). The same cleaning steps run once and are cached, and every chart and number is built from the **filtered** data, so they all respond to the sidebar filters.

## 4. Dashboard features

- **6 KPIs:** total incidents, total deaths, average deaths per incident, deadliest single incident, peak year, and top state.
- **Filters:** a Year range slider and a State multi-select.
- **Incident trend:** incidents per year, a monthly trend line, and incidents by calendar month.
- **State analysis:** top-N states by incidents (I choose N), an incidents-vs-deaths scatter plot, and a state summary table.
- **Death analysis:** deaths per year, top 10 states by deaths, distribution of deaths per incident, and the 10 deadliest incidents.
- **Causes and patterns:** top causes ranked by deaths or incidents, incidents by day of the week, and a year-by-month heatmap.
- **Data table and download:** a searchable table of the filtered records with a CSV download button.

## 5. Some findings

- The deadliest single record in my notebook was a flooding event in Niger State in May 2025 with **440 deaths**.
- The 10 deadliest incidents account for only about **4.4%** of all deaths. Most of the toll comes from a very large number of small incidents (the median incident has just 1 death), not a few huge ones.
- Road crashes and banditry-related incidents are the leading causes of death in the data.

_The dashboard lets you check these yourself and see how they change by year and state._

## 6. Tools used

- **Python 3.12**
- **pandas** for cleaning and analysis
- **matplotlib / seaborn** for notebook charts
- **Plotly** for interactive dashboard charts
- **Streamlit** for the web app
- **VS Code** and **Jupyter** for development
- **Git / GitHub** for version control

## 7. Project structure

```
incidents-dashboard/
├── app.py                  # Streamlit dashboard
├── incident.ipynb          # Notebook with the original analysis
├── incidents_updated.csv   # Raw data
├── requirements.txt        # Python packages needed
└── README.md               # This file
```

## 8. How to run it

1. Clone or download this repository.
2. (Recommended) create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
   On Windows PowerShell, if scripts are blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once first.
3. Install the packages:
   ```
   python -m pip install -r requirements.txt
   ```
4. Start the app:
   ```
   python -m streamlit run app.py
   ```
5. Open `http://localhost:8501` in the browser if it does not open on its own.

Keep `incidents_updated.csv` in the same folder as `app.py`. If it is missing, the app shows an upload box.

## 9. Challenges and what I learned

- **Dirty location data.** The State values needed careful cleaning. I learned to inspect `unique()` values before trusting a column, and to label uncertain rows `Unknown` rather than force a match.
- **Virtual environments and terminals.** I ran into PowerShell blocking scripts, Python running in the wrong environment, and mixing up the Python shell (`>>>`) with the normal terminal. Using `python -m pip` and `python -m streamlit` keeps everything on the same Python.
- **From notebook to app.** In Streamlit the script re-runs on every click, so I learned to cache the data preparation with `@st.cache_data` and to build every chart from one filtered DataFrame.

## 10. Limitations

- State names come from the end of each title, so a few records may still be mapped imperfectly or shown as `Unknown`.
- The data reflects recorded incidents only. Differences between years or states can partly reflect how well events were reported.
- Death counts are as recorded in the source file, and I did not independently verify them.

## 11. Future improvements

- Add a map of Nigeria with incidents by state.
- Add a Cause filter and a date-range picker.
- Compare two states side by side.
- Deploy the app to Streamlit Community Cloud.

## 12. My Contact


GitHub: https://github.com/oppssy08/opeyemi-olorunfemi_incident_project-/upload
Email: opeyemi.olorunfemi81@gmail.com
