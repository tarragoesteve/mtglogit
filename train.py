"""Model training and evaluation."""

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MaxAbsScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score, accuracy_score


def train_model(X, y, l1_ratio=0.5, C=1.0, max_iter=1000, test_size=0.2, random_state=42):
    """Train logistic regression with elastic net and evaluate.
    
    Returns:
        model: fitted LogisticRegression
        scaler: fitted MaxAbsScaler
        metrics: dict with train/test log_loss, auc, accuracy
    """
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    print(f"  Train: {X_train.shape[0]} games, Test: {X_test.shape[0]} games")
    print(f"  Win rate - Train: {y_train.mean():.3f}, Test: {y_test.mean():.3f}")

    # Scale features (MaxAbsScaler preserves sparsity)
    scaler = MaxAbsScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Fit logistic regression
    print(f"  Training LogisticRegression (C={C}, l1_ratio={l1_ratio}, solver=saga)...")
    model = LogisticRegression(
        solver="saga",
        l1_ratio=l1_ratio,
        C=C,
        max_iter=max_iter,
        random_state=random_state,
    )
    model.fit(X_train_s, y_train)

    # Evaluate
    metrics = {}
    for split_name, X_s, y_true in [("train", X_train_s, y_train), ("test", X_test_s, y_test)]:
        y_prob = model.predict_proba(X_s)[:, 1]
        y_pred = model.predict(X_s)
        metrics[f"{split_name}_log_loss"] = log_loss(y_true, y_prob)
        metrics[f"{split_name}_auc"] = roc_auc_score(y_true, y_prob)
        metrics[f"{split_name}_accuracy"] = accuracy_score(y_true, y_pred)

    print(f"  Results:")
    print(f"    Train - Log Loss: {metrics['train_log_loss']:.4f}, AUC: {metrics['train_auc']:.4f}, Acc: {metrics['train_accuracy']:.4f}")
    print(f"    Test  - Log Loss: {metrics['test_log_loss']:.4f}, AUC: {metrics['test_auc']:.4f}, Acc: {metrics['test_accuracy']:.4f}")
    gap = metrics["train_log_loss"] - metrics["test_log_loss"]
    print(f"    Log Loss gap (train-test): {gap:.4f}", "(possible overfitting)" if abs(gap) > 0.05 else "(OK)")

    nonzero = np.count_nonzero(model.coef_)
    print(f"  Non-zero coefficients: {nonzero} / {model.coef_.shape[1]}")

    return model, scaler, metrics
