# dataset-pyday-bcn-2021

<details>
<summary>0. Repo setup (already run for you)
</summary>

```
git clone git@github.com:daavoo/dataset-pyday-bcn-2021.git
cd dataset-pyday-bcn-2021
```

```
pip install -r requirements.txt
```

```
# https://dvc.org/doc/command-reference/init
dvc init
```

</details>

---

You should be able to follow all the steps bellow without leaving the browser.

---

## 1. Fork this repo

- https://github.com/daavoo/dataset-pyday-bcn-2021

More info: https://docs.github.com/en/get-started/quickstart/fork-a-repo

---

## 2. Open fork in online code editor

Navigate to your for fork and press `.` or change the URL from "github.com" to "github.dev"

More info: https://docs.github.com/en/codespaces/the-githubdev-web-based-editor

---

## 3. Setup DVC Remote

<details>
<summary>Add remote to `.dvc/config`</summary>

```
['remote "myremote"']
    url = gdrive://YOUR_URL
```

More info: https://dvc.org/doc/user-guide/setup-google-drive-remote

Other remote type? No problemo: 

https://dvc.org/doc/command-reference/remote/add#supported-storage-types

</details>

## 4. Setup DVC Pipeline

<details>
<summary>Create `params.yaml`</summary>

More info: https://dvc.org/doc/command-reference/params#description

```yaml
repo: daavoo/data-source-pyday-bcn-2021

labels:
- Comida
- Hobby
- Libro

state: open
since: 2021/1/1
until: 2021/11/23

data_folder: data
```

</details>


<details>
<summary>Create `dvc.yaml`</summary>

More info: https://dvc.org/doc/user-guide/project-structure/pipelines-files

```yaml
stages:
  get-data:
    cmd: python src/get_data.py
      --output_folder ${data_folder}
    deps:
      - src/get_data.py
    params:
      - repo
      - labels
      - state
      - since
      - until
    outs:
      - ${data_folder}
  
  data-metrics:
    cmd: python src/compute_metrics.py
      --input_folder ${data_folder}
      --output_metrics_file ${metrics_file}
    deps:
      - src/compute_metrics.py
      - ${data_folder}
    metrics:
      - ${metrics_file}:
          cache: false
```

</details>

<details>
<summary>Create `src/get_data.py`</summary>

```py
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
```

</details>


<details>
<summary>Create `src/compute_metrics.py`</summary>

```py
import json
from pathlib import Path

import fire
from loguru import logger


def compute_metrics(input_folder, output_metrics_file):
    data_path = Path(input_folder)
    metrics = {}
    for label_folder in data_path.iterdir():
        metrics[label_folder.name] = len(list(label_folder.iterdir()))

    for name, amount in metrics.items():
        logger.info(f"LABEL: {name}: {amount}")

    with open(output_metrics_file, "w") as f:
        json.dump(metrics, f, indent=4)


if __name__ == "__main__":
    fire.Fire(compute_metrics)
```

</details>

---

## 5. Set Up `On Pull Request` Workflow


<details>
<summary>Create `secrets.GDRIVE_CREDENTIALS_DATA`</summary>

- Get the content:
https://colab.research.google.com/drive/1Xe96hFDCrzL-Vt4Zj-cVHOxUgu-fyuBW

More info: https://dvc.org/doc/user-guide/setup-google-drive-remote#authorization

- Add new secret:
https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository

</details>

<details>
<summary>Create `on_pr.yml`</summary>

More info:

- `dvc pull`: https://dvc.org/doc/command-reference/pull
- `dvc push`: https://dvc.org/doc/command-reference/push

- `dvc exp run`: https://dvc.org/doc/command-reference/exp/run
- `dvc exp diff`: https://dvc.org/doc/command-reference/exp/diff

- `cml pr`: https://cml.dev/doc/ref/pr
- `cml send-comment`: https://cml.dev/doc/ref/send-comment

Need to scale? No problemo: 

https://cml.dev/doc/self-hosted-runners

```yaml
name: DVC & CML Workflow on Pull Request

on:
  pull_request:
    branches: [ main ]

  # Allows you to run this workflow manually from the Actions tab
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    container: docker://ghcr.io/iterative/cml:latest

    steps:
      - uses: actions/checkout@v2
        with:
          fetch-depth: 0

      - name: Setup
        env:
          GDRIVE_CREDENTIALS_DATA: ${{ secrets.GDRIVE_CREDENTIALS_DATA }}
        run: |
          pip install -r requirements.txt
          dvc pull

      - name: Run DVC pipeline
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          dvc exp run

      - name: Push changes
        env:
          GDRIVE_CREDENTIALS_DATA: ${{ secrets.GDRIVE_CREDENTIALS_DATA }}
        run: |
          dvc push

      - name: CML PR 
        env:
          REPO_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          cml pr "data.*" "dvc.lock" "params.yaml"

      - name: CML Report
        env:
          REPO_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "## Metrics & Params" >> report.md
          dvc exp diff main --old --show-md >> report.md
          cml send-comment --pr --update report.md
```

</details>

---

## 5. Run Pipeline from Github


---

## 6. Run Pipeline from Studio

- https://studio.iterative.ai

- Access studio view: https://dvc.org/doc/studio/get-started

- Run the pipeline editing the params: https://dvc.org/doc/studio/user-guide/run-experiments

---

## 7. Set Up Weekly Workflow


<details>
<summary>Create `weekly.yml`</summary>

```yaml
name: DVC & CML Weekly Workflow

on:
  schedule:
    - cron: "0 0 * * 0"

  # Allows you to run this workflow manually from the Actions tab
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    container: docker://ghcr.io/iterative/cml:latest

    steps:
      - uses: actions/checkout@v2
        with:
          fetch-depth: 0

      - name: Setup
        env:
          GDRIVE_CREDENTIALS_DATA: ${{ secrets.GDRIVE_CREDENTIALS_DATA }}
        run: |
          pip install -r requirements.txt
          dvc pull

      - name: Run DVC pipeline
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          dvc exp run -S until=$(date +'%Y/%m/%d')

      - name: Push changes
        env:
          GDRIVE_CREDENTIALS_DATA: ${{ secrets.GDRIVE_CREDENTIALS_DATA }}
        run: |
          dvc push

      - name: CML PR 
        env:
          REPO_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          cml pr "data.*" "dvc.lock" "params.yaml"

      - name: CML Report
        env:
          REPO_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "## Metrics & Params" >> report.md
          dvc exp diff main --old --show-md >> report.md
          cml send-comment --pr --update --commit-sha=HEAD report.md
```

</details>

## 8. Operation Vacation
