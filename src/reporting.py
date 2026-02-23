from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve


def save_confusion_matrix_plot(cm: np.ndarray, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.figure.colorbar(im, ax=ax)

    ax.set_xticks([0, 1, 2])
    ax.set_yticks([0, 1, 2])
    ax.set_xticklabels(["H", "D", "A"])
    ax.set_yticklabels(["H", "D", "A"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix")

    for i in range(3):
        for j in range(3):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", color="black")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_calibration_plot(y_true: np.ndarray, proba: np.ndarray, out_path: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    class_names = ["H", "D", "A"]

    for class_idx, class_name in enumerate(class_names):
        binary_true = (y_true == class_idx).astype(int)
        frac_pos, mean_pred = calibration_curve(binary_true, proba[:, class_idx], n_bins=10, strategy="quantile")
        ax.plot(mean_pred, frac_pos, marker="o", label=class_name)

    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="perfect")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title("Calibration Curve (One-vs-Rest)")
    ax.legend()

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
