# Data Versioning (DVC)

## Source

- **Dataset**: SemEval-2014 Task 4, Restaurant aspect-based sentiment analysis.
- **Origin**: the SemEval-2014 shared task (original data requires registration at
  `alt.qcri.org`). We use the widely-cited mirror in
  `songyouwei/ABSA-PyTorch` (`datasets/semeval14`).
- **License**: research use (shared-task benchmark data).
- **Format**: "segmented" triples — one sentence (target term replaced by `$T$`),
  the target term, and the polarity (`-1`/`0`/`1`) per line.

The raw data is **not committed to git**; it lives in DVC remote storage
(MS Azure Blob), and git only stores the small `.dvc` pointer files.

## How data is versioned

```bash
dvc add data/raw data/processed     # creates .dvc files
git add data.dvc ...                # commit the pointer files
dvc push                            # upload actual data to Azure
```

The DVC remote is Azure Blob Storage (`azure://dvc`, account `wut2026`), configured
in `.dvc/config`. The account key / connection string is a secret and lives in
`.dvc/config.local` (gitignored) — set it before running `dvc push`:

```bash
dvc remote modify myazure connection_string "<your Azure connection string>"
```

## Dataset versions

| Version | Path | Description |
|---------|------|-------------|
| v1 | `data/processed/{train,test}_v1.csv` | Minimal parse: inject the target term, keep text as-is. |
| v2 | `data/processed/{train,test}_v2.csv` | Cleaned: lowercased, normalized parentheses (`-LRB-`/`-RRB-`), collapsed whitespace, deduplicated `(text, term, label)` rows. |

### What changed v1 -> v2

- Lowercased all text and terms (reduces vocabulary sparsity).
- Replaced `-LRB-` / `-RRB-` tokenization artifacts with parentheses.
- Collapsed whitespace and removed stray backticks.
- Removed duplicate `(text, term, label)` records.

### Raw counts

- Train: 3608 instances (positive 2164 / negative 807 / neutral 637).
- Test: 1120 instances (positive 728 / negative 196 / neutral 196).
- v2 deduplication removed a small number of duplicate rows (see pipeline output).

## Linking code -> data

Each MLflow run logs `train_checksum` (MD5 of the training CSV) and `data_version`,
so a model can always be traced back to the exact dataset that produced it.
