"""Streamlit UI: upload a resume -> ranked jobs, match scores, skill gaps and recommendations.

Run:  streamlit run app.py
"""

from __future__ import annotations

import html
import io
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.matcher import AVAILABLE_MODELS
from src.parser import extract_text
from src.pipeline import DEFAULT_JOBS, MatchingPipeline, load_jobs, normalize_jobs

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "data" / "sample_resumes"
RESULTS = ROOT / "results" / "eval_results.md"
BAR_COLOR = "#2a78d6"
METHOD_LABELS = {"Hybrid (SBERT + skills + experience)": "hybrid",
                 "SBERT semantic only": "sbert", "TF-IDF baseline": "tfidf"}

st.set_page_config(page_title="Resume–Job Matcher", page_icon="🎯", layout="wide")
st.markdown("""
<style>
.chip{display:inline-block;padding:2px 10px;margin:2px 4px 2px 0;border-radius:12px;font-size:0.85rem;
      border:1px solid rgba(128,128,128,.35)}
.chip.ok{background:rgba(34,160,90,.15)} .chip.part{background:rgba(230,160,20,.18)}
.chip.miss{background:rgba(220,60,60,.15)} .chip.pref{background:rgba(128,128,128,.12)}
</style>""", unsafe_allow_html=True)


def chips(items, kind: str, empty: str = "—") -> str:
    if not items:
        return f"<span style='opacity:.6'>{empty}</span>"
    return "".join(f"<span class='chip {kind}'>{html.escape(str(i))}</span>" for i in items)


@st.cache_resource(show_spinner="Loading the Transformer model and indexing jobs (first run downloads the model)…")
def get_pipeline(jobs_json: str, model_name: str) -> MatchingPipeline:
    return MatchingPipeline(pd.read_json(io.StringIO(jobs_json)), model_name=model_name)


# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    model_label = st.selectbox("Sentence Transformer model", list(AVAILABLE_MODELS))
    method_label = st.radio("Ranking method", list(METHOD_LABELS))
    method = METHOD_LABELS[method_label]
    top_k = st.slider("Number of jobs to show", 3, 20, 5)
    w_sem, w_skill, w_exp = 0.5, 0.4, 0.1
    if method == "hybrid":
        with st.expander("Hybrid score weights"):
            w_sem = st.slider("Semantic similarity", 0.0, 1.0, 0.5, 0.05)
            w_skill = st.slider("Skill coverage", 0.0, 1.0, 0.4, 0.05)
            w_exp = st.slider("Experience fit", 0.0, 1.0, 0.1, 0.05)
    st.divider()
    st.subheader("Job dataset")
    jobs_file = st.file_uploader("Optional: upload jobs CSV (needs title & description columns)", type=["csv"])
    if jobs_file is not None:
        try:
            jobs_df = normalize_jobs(pd.read_csv(jobs_file), limit=2000)
            st.caption(f"Using uploaded jobs: {len(jobs_df)}")
        except Exception as e:  # noqa: BLE001 - show any parsing problem to the user
            st.error(f"Could not read jobs file: {e}")
            jobs_df = load_jobs(DEFAULT_JOBS)
    else:
        jobs_df = load_jobs(DEFAULT_JOBS)
        st.caption(f"Using built-in sample jobs: {len(jobs_df)}")

pipe = get_pipeline(jobs_df.to_json(), AVAILABLE_MODELS[model_label])

# ----------------------------------------------------------------------------- input
st.title("🎯 AI Resume–Job Matching & Skill Gap Analysis")
st.caption("NLP + Transformer-based semantic similarity (Sentence-BERT) compared with a TF-IDF baseline.")

src_upload, src_sample, src_paste = st.tabs(["📄 Upload resume", "🧪 Use a sample resume", "✍️ Paste text"])
resume_text = None
with src_upload:
    up = st.file_uploader("Resume (PDF, DOCX or TXT)", type=["pdf", "docx", "txt"])
    if up is not None:
        try:
            resume_text = extract_text(up.getvalue(), up.name)
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not read the file: {e}")
with src_sample:
    samples = sorted(p.name for p in SAMPLES.glob("*.txt"))
    pick = st.selectbox("Sample resume", ["—"] + samples, key="sample")
    if pick != "—" and up is None:
        resume_text = (SAMPLES / pick).read_text(encoding="utf-8")
with src_paste:
    pasted = st.text_area("Paste resume text", height=200)
    if pasted.strip() and up is None and pick == "—":
        resume_text = pasted

if st.button("🔍 Analyze resume", type="primary", disabled=not resume_text):
    if len(resume_text.split()) < 30:
        st.warning("The resume text is very short (or the PDF is scanned/image-only), so results may be weak.")
    with st.spinner("Parsing resume, extracting skills and ranking jobs…"):
        st.session_state["text"] = resume_text
        st.session_state["result"] = pipe.match(resume_text, method=method, top_k=top_k,
                                                w_semantic=w_sem, w_skills=w_skill, w_experience=w_exp)
        st.session_state["top_k"] = top_k

if "result" not in st.session_state:
    st.info("Upload a resume (or pick a sample) and click **Analyze resume**.")
    st.stop()

res = st.session_state["result"]
text = st.session_state["text"]
top = res.ranking.head(st.session_state["top_k"])
profile = res.profile

t_match, t_gap, t_profile, t_compare, t_eval = st.tabs(
    ["🎯 Job matches", "🧩 Skill gap & recommendations", "👤 Candidate profile",
     "⚖️ TF-IDF vs SBERT", "📊 Evaluation"])

# ----------------------------------------------------------------------------- matches
with t_match:
    st.subheader(f"Top {len(top)} jobs — ranked by {method_label}")
    for i, job in top.iterrows():
        gap = res.gaps[job["job_id"]]
        score_txt = (f"match {job['match_score'] * 100:.0f}%" if method == "hybrid"
                     else f"cosine {job['match_score']:.3f}")
        with st.expander(f"#{i + 1}  {job['title']} — {job['company']}   ·   {score_txt}", expanded=i == 0):
            c = st.columns(4)
            c[0].metric("Hybrid score", f"{job['hybrid_score'] * 100:.0f}%")
            c[1].metric("SBERT cosine", f"{job['sbert_score']:.3f}")
            c[2].metric("TF-IDF cosine", f"{job['tfidf_score']:.3f}")
            c[3].metric("Skill coverage", "n/a" if pd.isna(job["skill_score"]) else f"{job['skill_score'] * 100:.0f}%")
            st.caption(f"{job['category']} · {job['location']} · "
                       f"min. experience: {job['min_years']:.0f} yrs (yours ≈ {profile.experience_years} yrs)")

            st.markdown("**✅ Matched skills** " + chips(gap.matched, "ok"), unsafe_allow_html=True)
            st.markdown("**🟡 Partially covered (related skill)** " + chips(
                [f"{p['job_skill']} ≈ {p['candidate_skill']}" for p in gap.partial], "part"), unsafe_allow_html=True)
            st.markdown("**❌ Missing required** " + chips(gap.missing_required, "miss", "none 🎉"),
                        unsafe_allow_html=True)
            st.markdown("**➕ Missing preferred / nice-to-have** " + chips(gap.missing_preferred, "pref", "none"),
                        unsafe_allow_html=True)

            st.markdown("**Why this match? (semantic evidence)**")
            for ev in pipe.explain(text, job["job_id"]):
                st.markdown(f"- Job asks: *{ev['job_requirement']}*  \n"
                            f"  Resume shows: *{ev['resume_evidence']}*  (similarity {ev['similarity']:.2f})")
            kw = pipe.keyword_overlap(text, job["job_id"])
            if kw:
                st.caption("Top shared keywords (TF-IDF): " + ", ".join(kw))

# ----------------------------------------------------------------------------- skill gap
with t_gap:
    st.subheader("Recommended skills to develop")
    st.caption(f"Aggregated over your top {len(top)} jobs. Priority = 2 × jobs that require it + "
               "1 × jobs that prefer it (half weight if you already have a related skill).")
    recs = res.recommendations
    if recs.empty:
        st.success("No missing skills for your top jobs. 🎉")
    else:
        fig = px.bar(recs.sort_values("Priority"), x="Priority", y="Skill", orientation="h",
                     hover_data={"Category": True, "Needed by (top jobs)": True, "Priority": True, "Skill": False})
        fig.update_traces(marker_color=BAR_COLOR, marker_line_width=0)
        fig.update_layout(height=40 * len(recs) + 80, margin=dict(l=10, r=10, t=10, b=10),
                          yaxis_title=None, xaxis_title="Priority", bargap=0.35)
        st.plotly_chart(fig, width="stretch")
        st.dataframe(recs, width="stretch", hide_index=True)

    st.subheader("Gap report for one job")
    titles = {f"{r['title']} — {r['company']}": r["job_id"] for _, r in top.iterrows()}
    chosen = titles[st.selectbox("Job", list(titles))]
    g = res.gaps[chosen]
    jrow = res.ranking[res.ranking["job_id"] == chosen].iloc[0]
    rows = ([{"Skill": s, "Type": "Required", "Status": "✅ Have"} for s in g.matched_required]
            + [{"Skill": s, "Type": "Preferred", "Status": "✅ Have"} for s in g.matched_preferred]
            + [{"Skill": p["job_skill"], "Type": p["type"].title(),
                "Status": f"🟡 Related: {p['candidate_skill']} ({p['similarity']:.2f})"} for p in g.partial]
            + [{"Skill": s, "Type": "Required", "Status": "❌ Missing"} for s in g.missing_required]
            + [{"Skill": s, "Type": "Preferred", "Status": "➖ Missing"} for s in g.missing_preferred])
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    report = {"candidate": profile.name, "job": jrow["title"], "company": jrow["company"],
              "hybrid_score": round(float(jrow["hybrid_score"]), 3),
              "matched": g.matched, "partial": g.partial,
              "missing_required": g.missing_required, "missing_preferred": g.missing_preferred}
    st.download_button("⬇️ Download gap report (JSON)", json.dumps(report, indent=2),
                       file_name=f"skill_gap_{chosen}.json", mime="application/json")

# ----------------------------------------------------------------------------- profile
with t_profile:
    st.subheader("Extracted candidate profile")
    c = st.columns(4)
    c[0].metric("Name", profile.name or "—")
    c[1].metric("Highest degree", profile.highest_degree or "—")
    c[2].metric("Experience (est.)", f"{profile.experience_years} yrs")
    c[3].metric("Skills found", len(profile.skills))
    st.write(f"📧 {profile.email or '—'}   ·   📞 {profile.phone or '—'}   ·   🔗 {', '.join(profile.links) or '—'}")
    st.markdown("**Skills by category**")
    for cat, skills in profile.skills_by_category.items():
        st.markdown(f"*{cat}:* " + chips(skills, "ok"), unsafe_allow_html=True)
    if profile.education:
        st.markdown("**Education**")
        st.dataframe(pd.DataFrame(profile.education), width="stretch", hide_index=True)
    st.markdown("**Detected resume sections**")
    for name, body in profile.sections.items():
        with st.expander(name.title()):
            st.text(body)

# ----------------------------------------------------------------------------- comparison
with t_compare:
    st.subheader("Baseline (TF-IDF) vs proposed (SBERT) for this resume")
    cmp = res.ranking[["title", "company", "tfidf_rank", "sbert_rank", "hybrid_rank",
                       "tfidf_score", "sbert_score", "hybrid_score"]].sort_values("hybrid_rank")
    rho = res.ranking["tfidf_score"].corr(res.ranking["sbert_score"], method="spearman")
    st.caption(f"Spearman rank correlation between TF-IDF and SBERT scores: **{rho:.2f}** "
               "(1 = identical ranking). Jobs where ranks differ a lot are where semantic matching "
               "finds related wording that keywords miss, or vice-versa.")
    st.dataframe(cmp.head(max(10, len(top))), width="stretch", hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="%.3f")
                                for c in ("tfidf_score", "sbert_score", "hybrid_score")})
    fig = px.scatter(res.ranking, x="tfidf_score", y="sbert_score", hover_name="title",
                     hover_data={"company": True, "tfidf_score": ":.3f", "sbert_score": ":.3f"},
                     labels={"tfidf_score": "TF-IDF cosine", "sbert_score": "SBERT cosine"})
    fig.update_traces(marker=dict(size=10, color=BAR_COLOR, line=dict(width=2, color="white")))
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

# ----------------------------------------------------------------------------- evaluation
with t_eval:
    st.subheader("Experimental results")
    st.caption("Generated by `python evaluate.py` on the hand-labelled sample set "
               "(or a Kaggle resume dataset with `--kaggle-resumes`).")
    if st.button("▶️ Run evaluation now (built-in sample set)"):
        import evaluate as ev
        with st.spinner("Evaluating…"):
            texts, gold, relevant, names = ev.load_annotated(ROOT / "data" / "eval" / "annotations.json")
            eval_pipe = get_pipeline(load_jobs(DEFAULT_JOBS).to_json(), AVAILABLE_MODELS[model_label])
            preds = [set(eval_pipe.extractor.extract(t)) for t in texts]
            from datetime import datetime
            from src.evaluation import extraction_scores
            results = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                       "model": AVAILABLE_MODELS[model_label], "n_jobs": len(eval_pipe.jobs),
                       "dataset": f"hand-labelled sample ({len(texts)} resumes)",
                       "extraction": extraction_scores(preds, gold),
                       "ranking": ev.run_ranking(eval_pipe, texts, relevant)}
            RESULTS.parent.mkdir(exist_ok=True)
            RESULTS.write_text(ev.to_markdown(results), encoding="utf-8")
    if RESULTS.exists():
        st.markdown(RESULTS.read_text(encoding="utf-8"))
    else:
        st.info("No results yet — click the button above or run `python evaluate.py`.")
