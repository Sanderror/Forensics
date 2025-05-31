import streamlit as st
import pandas as pd
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode
import altair as alt
import streamlit.components.v1 as components
import ast
import pickle
from lime.lime_text import LimeTextExplainer


st.title("💊 Potential Drugs Dashboard")
st.markdown("""
This dashboard displays all **potentially unknown NPS names** (we will refer to them as **Potential Drugs** from now on) extracted from forum messages, 
along with the model's predicted likelihood that each term refers to an actual **drug**.

The dashboard displays:

- A table containing all the **predicted new drug names**
- **Filters** to make the table conform to your wishes
- Option to **download** the filtered table of potential drugs
- Insights into the **most similar known drugs** to the selected potential drug
- Insights into the **usage** of the selected potential drug term **over time**
- Observe **contexts** of a selected potential drug to see why it has been classified as such
""")

st.markdown('---')
st.subheader('🆕 Potential Drugs')
# Load dataset with for every term its contexts
@st.cache_data
def load_context_df():
    return pd.read_csv("candidate_predictions_final.csv")
context_df = load_context_df()

# Load pipeline for predicting the contexts, in order to get LIME explanations
@st.cache_data
def load_pipeline():
    with open('pipeline_final.pkl', 'rb') as f:
        pipeline = pickle.load(f)
    return pipeline
pipeline = load_pipeline()
class_names = pipeline.named_steps['clf'].classes_
# Lime explainer for contexts of candidates
explainer = LimeTextExplainer(class_names=class_names)

# Load your term scores from CSV
if "term_scores" not in st.session_state:
    st.session_state.term_scores = pd.read_csv("term_scores_final.csv")

term_scores = st.session_state.term_scores
term_scores = term_scores.rename(columns={'term':'potential drug', 'mean_prob':'likelihood', 'num_contexts':'nr of contexts', 'num_messages':'nr of messages', 'num_users':'nr of users'})
term_scores['likelihood'] = term_scores['likelihood'].apply(lambda x: round(x, 3))
# --- Sidebar filters ---
st.sidebar.header("🔍 Filters")
min_prob = st.sidebar.slider("Minimum likelihood of being a drug", 0.0, 1.0, 0.75, 0.01)
min_contexts = st.sidebar.number_input("Minimum number of contexts", value=20, step=1)
min_messages = st.sidebar.number_input("Minimum number of messages", value=20, step=1)
min_users = st.sidebar.number_input("Minimum number of different users", value=5, step=1)

# --- Filtered view of candidate list ---
filtered = term_scores[
    (term_scores['likelihood'] >= min_prob) &
    (term_scores['nr of contexts'] >= min_contexts) &
    (term_scores['nr of messages'] >= min_messages) &
    (term_scores['nr of users'] >= min_users)
][['potential drug', 'likelihood', 'nr of contexts', 'nr of messages', 'nr of users']]

st.metric(label="Total candidate terms", value=len(term_scores))
st.metric(label="Terms matching current filters", value=len(filtered))

gb = GridOptionsBuilder.from_dataframe(filtered.reset_index(drop=True))
gb.configure_selection('single', use_checkbox=False)
grid_options = gb.build()

grid_response = AgGrid(
    filtered.reset_index(drop=True),
    gridOptions=grid_options,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    height=323,
    fit_columns_on_grid_load=True
)

# Obtain the selected candidate in the table
selected = grid_response['selected_rows']
if selected is None or (isinstance(selected, pd.DataFrame) and selected.empty):
    selected = filtered.iloc[[0]]

# Optional: Download link
st.download_button("Download filtered results as CSV", data=filtered.to_csv(index=False), file_name="filtered_term_scores.csv", mime="text/csv")

# --- Load drug messages data ---
@st.cache_data
def load_drug_data():
    df = pd.read_csv("drugs_data_cleaned_final.csv", parse_dates=["Timestamp"])
    return df

# Set these values for plotting
drug_data = load_drug_data()
x_min = pd.Timestamp('2024-05')
x_max = pd.Timestamp('2025-04')

# Show the in depth analysis of a selected candidate term
if not selected.empty:
    selected_term = selected['potential drug'].iloc[0]
    st.markdown('---')
    st.subheader(f"🧪 Potential Drug Selected: `{selected_term}`")
    st.markdown("Select a **potential drug** in the table above to find the **most similar known drugs** and the **usage of the potential drug term over time**")

    # show similar drugs
    st.markdown('---')
    st.subheader("💊 Most Similar Known Drugs")

    similar_list = term_scores[term_scores['potential drug'] == selected_term]['similar_drugs'].iloc[0]
    if isinstance(similar_list, str):
        try:
            similar_list = ast.literal_eval(similar_list)
        except:
            similar_list = [similar_list]  # fallback
    if similar_list:
        # Create pill-style HTML badges
        badges_html = " ".join(
            [
                f"<span style='background-color:#e1f5fe; color:#0277bd; padding:6px 12px; border-radius:20px; margin:4px; display:inline-block;'>{drug}</span>"
                for drug in similar_list]
        )
        components.html(f"<div style='padding: 10px;'>{badges_html}</div>", height=100)
    else:
        st.info("No similar drugs listed for this term.")

    st.markdown('---')

    # --- Show drug term usage over time
    st.subheader("📈 Potential Drug Term Usage Over Time")

    # Filter messages that contain the selected term (case-insensitive)
    matches = drug_data[
        drug_data['Message'].str.contains(rf"\b{selected_term}\b", case=False, regex=True, na=False)
    ].copy()

    if not matches.empty:
        # Extract month from timestamp
        matches['month'] = matches['Timestamp'].dt.to_period('M').astype(str)

        # Count occurrences per month
        monthly_counts = matches.groupby('month').size().reset_index(name='count')

        # Sort months
        monthly_counts['month'] = pd.to_datetime(monthly_counts['month'])
        monthly_counts = monthly_counts.sort_values('month')
        # Line plot
        line_chart = alt.Chart(monthly_counts).mark_line(point=True).encode(
            x=alt.X('month:T', title='Month', axis=alt.Axis(format='%Y-%m'), scale=alt.Scale(domain=[2018, 2026])),
            y=alt.Y('count:Q', title=f'Messages containing "{selected_term}"'),
            tooltip=['month:T', 'count'],

        ).properties(width=700, height=400)

        st.altair_chart(line_chart, use_container_width=True)
    else:
        st.warning(f"No messages found containing the term '{selected_term}'.")

    st.markdown("---")
    # Create a lime explanation of the candidates contexts
    st.subheader("Observe Contexts Of Potential Drug Term")

    drug_contexts = context_df[context_df['term'] == selected_term]['context']
    num_contexts = len(drug_contexts)

    if "previous_selected_term" not in st.session_state:
        st.session_state.previous_selected_term = selected_term

    if st.session_state.previous_selected_term != selected_term:
        st.session_state.context_index = 0
        st.session_state.previous_selected_term = selected_term

    # Initialize session state for context index
    if "context_index" not in st.session_state:
        st.session_state.context_index = 0

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⟵ Prev") and st.session_state.context_index > 0:
            st.session_state.context_index -= 1
    with col3:
        if st.button("Next ⟶") and st.session_state.context_index < num_contexts - 1:
            st.session_state.context_index += 1

    # Show which context you're on
    st.write(f"Context {st.session_state.context_index + 1} of {num_contexts}")

    # Get the current context
    current_context = drug_contexts.iloc[st.session_state.context_index]

    # Generate LIME explanation
    explanation = explainer.explain_instance(
        current_context,
        pipeline.predict_proba,
        num_features=10
    )

    # Display explanation
    html = explanation.as_html()

    # Show modified HTML
    st.components.v1.html(html, height=600, scrolling=True)



