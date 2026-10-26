"""Smoke tests. Run: python -m pytest tests  (or: python tests/test_app.py)"""

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_skill_extraction_aliases_and_overlaps():
    from src.skills import get_skill_extractor
    ex = get_skill_extractor()
    skills = ex.extract("Worked with ReactJS, node.js, SQL Server and ASP.NET MVC. Let's rest and go.")
    assert {"React", "Node.js", "SQL Server", "ASP.NET"} <= set(skills)
    assert not {"SQL", "Go", "REST API", "Design Patterns"} & set(skills)


def test_job_requirement_split():
    from src.parser import split_job_requirements
    req, pref = split_job_requirements("Requirements:\n- Python\nNice to have:\n- Docker\n- Kubernetes")
    assert "Python" in req and "Docker" in pref and "Kubernetes" in pref


def test_experience_and_docx_parsing():
    import docx
    from src.parser import extract_text, parse_resume
    d = docx.Document()
    for line in ["Jane Doe", "jane@example.com", "Experience", "Developer, X (Jan 2020 - Dec 2021)",
                 "Education", "BS Computer Science, 2019"]:
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    profile = parse_resume(extract_text(buf.getvalue(), "cv.docx"))
    assert profile.name == "Jane Doe" and profile.email == "jane@example.com"
    assert profile.highest_degree == "Bachelor's"
    assert 1.8 <= profile.experience_years <= 2.1


def test_streamlit_app_end_to_end():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=300).run()
    assert not at.exception
    at.selectbox(key="sample").select("data_scientist.txt").run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    assert any("Machine Learning Engineer" in e.label for e in at.expander)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
