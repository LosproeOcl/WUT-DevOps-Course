# Data Versioning (DVC)

## Source

- **Dataset**: MAMS-ACSA (Aspect Category Sentiment Analysis), from the MAMS
  (Multi-Aspect Multi-Sentiment) project — `siat-nlp/MAMS-for-ABSA`.
- **Origin**: this raw snapshot contains the *English* restaurant reviews
  (reformatted from SemEval-2014) with per-sentence `<aspectCategory>` annotations.
  The full Chinese MAMS data (Dianping reviews) is a separate, much larger release.
- **License**: research use (shared-task benchmark data).
- **Format**: XML — each `<sentence>` has a `<text>` and a set of
  `<aspectCategory category="..." polarity="..."/>` elements.

The raw data is **not committed to git**; it lives in DVC remote storage, and git
only stores the small `.dvc` pointer files.

## How data is versioned

```bash
dvc add data/raw data/processed     # creates .dvc files
git add data.dvc ...                # commit the pointer files
dvc push                            # upload actual data to the DVC remote
```

The DVC remote is a **local directory** (`dvc-remote/`, remote `local`) that
simulates remote storage. It is gitignored, so git never sees the actual data.

## Aspect mapping

Fine-grained MAMS categories are merged into four coarse aspects:

| Aspect | Code | MAMS categories |
|--------|------|-----------------|
| 口味 (Taste/Food) | `food` | food, menu |
| 服务 (Service) | `service` | service, staff |
| 价格 (Price) | `price` | price |
| 环境 (Ambience) | `ambience` | ambience, place |

`miscellaneous` is dropped.

## Dataset versions

| Version | Path | Description |
|---------|------|-------------|
| v1 | `data/processed/{train,val,test}_v1.csv` | Minimal parse: extract (text, aspect, polarity) rows. |
| v2 | `data/processed/{train,val,test}_v2.csv` | Cleaned: lowercased, collapsed whitespace, deduplicated `(text, aspect, label)` rows. |

### What changed v1 -> v2

- Lowercased all text.
- Collapsed whitespace.
- Removed duplicate `(text, aspect, label)` records.

### Counts

- Raw aspect rows: 7660 (v2: 7511 after dedup).
- Per aspect (v2): food 3418 / service 2452 / price 405 / ambience 1236.

## Linking code -> data

Each MLflow run logs `train_checksum` (MD5 of the training CSV) and `data_version`,
so a model can always be traced back to the exact dataset that produced it.
