"""Weak supervision + synthetic data generation to bootstrap training labels."""

from .weak_rules import weak_label, LABEL_POS, LABEL_NEG, LABEL_ABSTAIN
from .synth import generate_dataset
from .dataset import LabelStore, split_of

__all__ = [
    "weak_label", "generate_dataset", "LabelStore", "split_of",
    "LABEL_POS", "LABEL_NEG", "LABEL_ABSTAIN",
]
