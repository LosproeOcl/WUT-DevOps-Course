"""Register the fine-tuned RoBERTa star-rating model to MLflow (DagsHub).

The RoBERTa rating model (``models/rating_bert/``) was fine-tuned on an AutoDL
RTX 3080 Ti (chinese-roberta-wwm-ext, MAX_LEN 384, 5 epochs, label smoothing).
This script wraps it as an ``mlflow.pyfunc`` model, logs the held-out metrics,
and registers it so it can be served / staged alongside the other models.

Usage (requires DagsHub tracking env vars):
    set DAGSHUB_REPO_OWNER=... DAGSHUB_REPO_NAME=... MLFLOW_TRACKING_USERNAME=... MLFLOW_TRACKING_PASSWORD=...
    python -m ml.register_rating_roberta
"""
from __future__ import annotations

import os

import mlflow
import mlflow.pyfunc
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "models", "rating_bert")
EXPERIMENT = "absa_restaurant_aspects"
MODEL_NAME = "absa_restaurant_rating_roberta"
MAX_LEN = 384

# Held-out metrics from the AutoDL training run (test split).
ACCURACY = 0.5923
MAE = 0.4460
ACC_WITHIN_1 = 0.9642


class RatingRoBERTaWrapper(mlflow.pyfunc.PythonModel):
    """pyfunc wrapper: tokenizer + RoBERTa with a 5-class star head."""

    def load_context(self, context):
        import torch
        from torch import nn
        from transformers import AutoModel, AutoTokenizer, BertConfig, RobertaConfig

        class _Model(nn.Module):
            def __init__(self, config):
                super().__init__()
                self.bert = AutoModel.from_config(config)
                self.head = nn.Linear(self.bert.config.hidden_size, 5)

            def forward(self, input_ids, attention_mask):
                out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
                return self.head(out.last_hidden_state[:, 0, :])

        model_dir = context.artifacts["model_dir"]
        data = torch.load(os.path.join(model_dir, "rating_bert.pt"), map_location="cpu", weights_only=False)
        config_dict = data["config"]
        config_cls = RobertaConfig if config_dict.get("model_type") == "roberta" else BertConfig
        self.model = _Model(config_cls.from_dict(config_dict))
        self.model.load_state_dict(data["state_dict"])
        self.model.eval()
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        for name, tok in (
            ("pad_token", "[PAD]"),
            ("unk_token", "[UNK]"),
            ("cls_token", "[CLS]"),
            ("sep_token", "[SEP]"),
            ("mask_token", "[MASK]"),
        ):
            if getattr(self.tokenizer, name) is None:
                setattr(self.tokenizer, name, tok)

    def predict(self, context, model_input):
        import torch

        texts = [str(x) for x in model_input.iloc[:, 0]]
        stars = []
        for text in texts:
            enc = self.tokenizer(text, max_length=MAX_LEN, truncation=True, padding="max_length", return_tensors="pt")
            with torch.no_grad():
                logits = self.model(enc["input_ids"], enc["attention_mask"])[0]
            stars.append(int(torch.softmax(logits, dim=0).argmax()) + 1)
        return pd.DataFrame({"star": stars})


def main() -> int:
    owner = os.environ.get("DAGSHUB_REPO_OWNER")
    name = os.environ.get("DAGSHUB_REPO_NAME")
    if owner and name:
        import dagshub

        dagshub.init(repo_owner=owner, repo_name=name, mlflow=True)
    mlflow.set_experiment(EXPERIMENT)

    if not os.path.exists(os.path.join(MODEL_DIR, "rating_bert.pt")):
        raise FileNotFoundError(f"rating model not found in {MODEL_DIR}; download it from AutoDL first")

    with mlflow.start_run(run_name="rating-roberta"):
        mlflow.log_param("task", "star_rating")
        mlflow.log_param("model", "RoBERTa (chinese-wwm-ext)")
        mlflow.log_param("max_len", MAX_LEN)
        mlflow.log_param("epochs", 5)
        mlflow.log_metric("rating_accuracy", ACCURACY)
        mlflow.log_metric("rating_mae", MAE)
        mlflow.log_metric("rating_acc_within_1", ACC_WITHIN_1)

        info = mlflow.pyfunc.log_model("rating_roberta", python_model=RatingRoBERTaWrapper(), artifacts={"model_dir": MODEL_DIR})
        mlflow.register_model(info.model_uri, MODEL_NAME)
        print(f"[rating-roberta] registered {MODEL_NAME} (accuracy={ACCURACY:.4f}, mae={MAE:.4f})")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
