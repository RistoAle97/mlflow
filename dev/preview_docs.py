import argparse
import os
import time
from urllib.parse import urlparse

import requests


class Session(requests.Session):
    def get(self, *args, **kwargs):
        resp = super().get(*args, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post(self, *args, **kwargs):
        resp = super().post(*args, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def patch(self, *args, **kwargs):
        resp = super().patch(*args, **kwargs)
        resp.raise_for_status()
        return resp.json()


MARKER = "<!-- documentation preview -->"


def upsert_comment(session, repo, pull_number, comment_body):
    comments = session.get(f"https://api.github.com/repos/{repo}/issues/{pull_number}/comments")
    preview_docs_comment = next(filter(lambda c: MARKER in c["body"], comments), None)
    comment_body_with_marker = MARKER + "\n\n" + comment_body
    if preview_docs_comment is None:
        print("Creating comment")
        session.post(
            f"https://api.github.com/repos/{repo}/issues/{pull_number}/comments",
            json={"body": comment_body_with_marker},
        )
    else:
        print("Updating comment")
        session.patch(preview_docs_comment["url"], json={"body": comment_body_with_marker})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--pull-number", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    args = parser.parse_args()

    github_session = Session()
    if github_token := os.environ.get("GITHUB_TOKEN"):
        github_session.headers.update({"Authorization": f"token {github_token}"})

    circle_session = Session()
    if circle_token := os.environ.get("CIRCLE_TOKEN"):
        circle_session.headers.update({"Circle-Token": circle_token})

    # Get the ID of the build_doc job
    repo = "mlflow/mlflow"
    build_doc_job_name = "build_doc"
    job_id = None
    workflow_run_link = f"https://github.com/{repo}/actions/runs/{args.workflow_run_id}"
    for _ in range(5):
        status = github_session.get(
            f"https://api.github.com/repos/{repo}/commits/{args.commit_sha}/status"
        )
        build_doc_status = next(
            filter(lambda s: s["context"].endswith(build_doc_job_name), status["statuses"]),
            None,
        )
        if build_doc_status:
            job_id = urlparse(build_doc_status["target_url"]).path.split("/")[-1]
            break
        print(f"Waiting for {build_doc_job_name} job status to be available...")
        time.sleep(3)
    else:
        print(f"Could not find {build_doc_job_name} job status")
        comment_body = f"""
Failed to find a documentation preview for {args.commit_sha}.

<details>
<summary>More info</summary>

- If the `ci/circleci: {build_doc_job_name}` job status is successful, you can see the preview with
  the following steps:
  1. Click `Details`.
  2. Click `Artifacts`.
  3. Click `docs/build/html/index.html`.
- This comment was created by {workflow_run_link}.

</details>
"""
        upsert_comment(github_session, repo, args.pull_number, comment_body)
        return

    # Get the artifact URL of the top level index.html
    for _ in range(5):
        try:
            # Despite using a valid CircleCI token, the request occasionally fails with a 403 error.
            job = circle_session.get(f"https://circleci.com/api/v2/project/gh/{repo}/job/{job_id}")
            job_url = job["web_url"]
            workflow_id = job["latest_workflow"]["id"]
            workflow = circle_session.get(f"https://circleci.com/api/v2/workflow/{workflow_id}/job")
            break
        except requests.HTTPError as e:
            print(
                f"Failed to get CircleCI job info: {e.response.status_code, e.response.text}, "
                f"retrying..."
            )
            time.sleep(1)
            continue
    else:
        upsert_comment(
            github_session,
            repo,
            args.pull_number,
            (
                f"Failed to find a documentation preview for {args.commit_sha}. "
                f"See {workflow_run_link} for what went wrong."
            ),
        )
        return

    build_doc_job = next(filter(lambda s: s["name"] == build_doc_job_name, workflow["items"]))
    build_doc_job_id = build_doc_job["id"]
    top_page = f"https://output.circle-artifacts.com/output/job/{build_doc_job_id}/artifacts/0/docs/build/latest/index.html"
    changed_pages = f"https://output.circle-artifacts.com/output/job/{build_doc_job_id}/artifacts/0/docs/build/latest/diff.html"

    # Post the artifact URL as a comment
    comment_body = f"""
Documentation preview for {args.commit_sha} will be available when [this CircleCI job]({job_url})
completes successfully. You may encounter a `{{"message":"not found"}}` error when reloading
a page. If so, add `/index.html` to the URL.

- [Top page]({top_page})
- [Changed pages]({changed_pages}) (⚠️ only MDX file changes are detected ⚠️)

<details>
<summary>More info</summary>

- Ignore this comment if this PR does not change the documentation.
- It takes a few minutes for the preview to be available.
- The preview is updated when a new commit is pushed to this PR.
- This comment was created by {workflow_run_link}.

</details>
"""
    upsert_comment(github_session, repo, args.pull_number, comment_body)


if __name__ == "__main__":
    main()
