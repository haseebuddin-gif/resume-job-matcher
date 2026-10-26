"""Deploy to Hugging Face Spaces (Docker SDK).

    set HF_TOKEN=hf_...   (a token with write access)
    python deploy_hf.py <username>/<space-name>
"""

import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent
SPACE_HEADER = """---
title: SkillMatch
emoji: 🎯
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Resume-job matching and skill gap analysis using NLP
---

"""
IGNORE = [".git/*", ".venv/*", ".cache/*", ".hf/*", "**/__pycache__/*", "*.pyc",
          "frontend/node_modules/*", "frontend/dist/*", "frontend/.angular/*", "frontend/.vscode/*",
          "data/external/*", "data/custom_jobs.json", "README.md"]


def main(repo_id: str):
    api = HfApi()
    api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(repo_id=repo_id, repo_type="space", folder_path=ROOT, ignore_patterns=IGNORE,
                      commit_message="Deploy SkillMatch")
    readme = SPACE_HEADER + (ROOT / "README.md").read_text(encoding="utf-8")
    api.upload_file(repo_id=repo_id, repo_type="space", path_or_fileobj=readme.encode("utf-8"),
                    path_in_repo="README.md", commit_message="Space README")
    print(f"https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main(sys.argv[1])
