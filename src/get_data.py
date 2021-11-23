import os
from datetime import datetime
from pathlib import Path

import fire
import yaml
from github import Github
from loguru import logger


def get_data(output_folder):
    with open("params.yaml") as f:
        params = yaml.safe_load(f)

    output_folder = Path(output_folder)
    for label in params["labels"]:
        (output_folder / label).mkdir(parents=True, exist_ok=True)

    since = datetime(*map(int, params["since"].split("/")))
    until = datetime(*map(int, params["until"].split("/")))
    logger.info(f"Getting issue labels since {since} until {until}")

    logger.info("Initializing Github")
    if os.environ.get("GITHUB_TOKEN"):
        g = Github(os.environ["GITHUB_TOKEN"])
    else:
        g = Github()

    logger.info(f"Querying repo: {params['repo']}")
    repo = g.get_repo(params["repo"])

    for issue in repo.get_issues(state=params["state"], since=since):
        issue_labels = [
            x.name for x in issue.labels if x.name in params["labels"]
        ]
    
        if (
            issue.pull_request 
            or issue.created_at > until
            or len(issue_labels) != 1
        ):
            logger.debug(f"Skipping issue: {issue.title}")
            logger.debug(f"Created at: {issue.created_at}")
            logger.debug(f"Labels: {issue.labels}")
            continue
    
        label = str(issue_labels[0])
        logger.info(f"TITLE:\n{issue.title}")
        logger.info(f"BODY:\n{issue.body}")
        logger.info(f"LABEL:\n{label}")

        output_file = output_folder / label / f"{issue.number}.txt"
        output_file.write_text(f"{issue.title}\n{issue.body}")


if __name__ == "__main__":
    fire.Fire(get_data)