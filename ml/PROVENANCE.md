# Provenance

Traceability from code and data to the deployed model.

## Model -> data

Each training run logs `train_checksum` (MD5 of the training CSV) and
`data_version` to MLflow, and DVC stores the dataset hash in `.dvc` files.
Together they answer: *"which exact dataset version produced this model?"*

## Model -> code

Each run logs `git_sha`, so a model artifact can be mapped back to the exact
commit of `ml/data_pipeline.py` and `ml/train.py` that produced it.

## Production model

The model served by the app is stored at `models/model.joblib` and is also
registered in MLflow. See `ml/registry/current_model.md` for the current
production designation.

## Reproducing a run

```bash
git checkout <git_sha>           # code
dvc checkout <dataset version>   # data
python ml/data_pipeline.py
python ml/train.py --data-version v2 --mode tuned
```
