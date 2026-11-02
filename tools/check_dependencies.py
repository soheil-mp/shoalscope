#!/usr/bin/env python3
"""Check dependencies against the licence and scope policy.

Policy (docs/research/03-technology-landscape.md §4 and ADR-0002):

* Licences must be permissive (MIT, BSD, Apache-2.0, ISC, MPL-2.0, PSF and similar), so the
  project can stay MIT. Copyleft and unknown licences fail unless listed in ``EXCEPTIONS``
  with a reason.
* Machine-learning frameworks, model runtimes, model-API clients, vector databases and
  experiment trackers are not allowed at all, and neither are packages known to be
  source-available or proprietary.

Two modes:

* ``python -m tools.check_dependencies`` checks every installed distribution (licence and
  scope); run it in the workspace environment.
* ``python -m tools.check_dependencies --lock`` checks the package names in ``uv.lock``
  against the deny-list without installing anything; pre-commit runs it on every lock change.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from importlib.metadata import Distribution, distributions
from pathlib import Path

LOCKFILE = Path(__file__).resolve().parent.parent / "uv.lock"

ALLOWED_SPDX = frozenset(
    {
        "0BSD",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "BSD-3-Clause-Clear",
        "BSL-1.0",
        "CC0-1.0",
        "HPND",
        "ISC",
        "MIT",
        "MIT-0",
        "MIT-CMU",
        "MPL-2.0",
        "PSF-2.0",
        "Python-2.0",
        "Unlicense",
        "Zlib",
        "BSD",  # family name used by older metadata; every BSD variant is permissive
    }
)

# Free-text `License:` values and trove classifiers seen in the wild, mapped to SPDX ids.
ALIASES = {
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "bsd": "BSD",
    "bsd 2-clause license": "BSD-2-Clause",
    "bsd 3-clause license": "BSD-3-Clause",
    "bsd license": "BSD",
    "bsd-3-clause": "BSD-3-Clause",
    "historical permission notice and disclaimer (hpnd)": "HPND",
    "isc license (iscl)": "ISC",
    "mit": "MIT",
    "mit license": "MIT",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "psf-2.0": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
    "simplified bsd": "BSD-2-Clause",
    "the unlicense (unlicense)": "Unlicense",
}

# Packages whose metadata is unusable but whose licence was checked by hand.
EXCEPTIONS: dict[str, str] = {}

# ADR-0002: no machine learning, model runtimes, model APIs or their infrastructure.
DENIED_ML = frozenset(
    {
        "accelerate",
        "anthropic",
        "catboost",
        "chromadb",
        "cohere",
        "diffusers",
        "dspy-ai",
        "faiss-cpu",
        "faiss-gpu",
        "fastai",
        "google-genai",
        "google-generativeai",
        "groq",
        "huggingface-hub",
        "instructor",
        "jax",
        "keras",
        "langchain",
        "lightgbm",
        "lightning",
        "litellm",
        "llama-cpp-python",
        "llama-index",
        "mistralai",
        "mlflow",
        "mxnet",
        "ollama",
        "onnx",
        "onnxruntime",
        "openai",
        "opencv-contrib-python",
        "opencv-python",
        "opencv-python-headless",
        "openvino",
        "paddlepaddle",
        "pinecone",
        "pinecone-client",
        "pycaret",
        "pytorch-lightning",
        "qdrant-client",
        "replicate",
        "safetensors",
        "scikit-learn",
        "sentence-transformers",
        "spacy",
        "tensorflow",
        "tflite-runtime",
        "timm",
        "tokenizers",
        "torch",
        "torchaudio",
        "torchvision",
        "transformers",
        "ultralytics",
        "vllm",
        "wandb",
        "weaviate-client",
        "xgboost",
    }
)
DENIED_ML_PREFIXES = ("langchain-", "llama-index-", "tensorflow-", "torch-", "openai-")

# Source-available or proprietary packages (technology landscape §1).
DENIED_LICENCE = {
    "dlthub": "commercial dltHub licence",
    "soda-core": "proprietary licence since 4.x",
}


@dataclass(frozen=True)
class Verdict:
    """Outcome of checking one distribution."""

    name: str
    licence: str
    ok: bool
    reason: str = ""


def normalise_name(name: str) -> str:
    """Normalise a distribution name as in PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def scope_violation(name: str) -> str | None:
    """Return why a package is out of scope, or None when it is allowed."""
    name = normalise_name(name)
    if name in DENIED_ML or name.startswith(DENIED_ML_PREFIXES):
        return "machine-learning package (ADR-0002)"
    if name in DENIED_LICENCE:
        return f"not open source: {DENIED_LICENCE[name]}"
    return None


def spdx_allowed(expression: str) -> bool:
    """Whether an SPDX expression is acceptable.

    `A OR B` passes when any option is allowed; otherwise every licence in the expression
    must be allowed. `WITH` exceptions are ignored for the decision.
    """
    expression = re.sub(r"\s+WITH\s+\S+", "", expression)
    tokens = [t for t in re.split(r"[()\s]+", expression) if t and t not in {"AND", "OR"}]
    if not tokens:
        return False
    if " OR " in expression:
        return any(t in ALLOWED_SPDX for t in tokens)
    return all(t in ALLOWED_SPDX for t in tokens)


def licence_of(dist: Distribution) -> str | None:
    """Best available SPDX expression for a distribution, or None if unknown."""
    meta = dist.metadata
    if expression := meta.get("License-Expression"):
        return str(expression)
    free_text = (meta.get("License") or "").strip()
    if free_text in ALLOWED_SPDX:
        return free_text
    if free_text.lower() in ALIASES:
        return ALIASES[free_text.lower()]
    for classifier in meta.get_all("Classifier") or []:
        if classifier.startswith("License ::"):
            leaf = classifier.split(" :: ")[-1].lower()
            if leaf in ALIASES:
                return ALIASES[leaf]
    return None


def check(dist: Distribution) -> Verdict:
    """Apply the scope and licence policy to one installed distribution."""
    name = normalise_name(dist.metadata["Name"])
    if reason := scope_violation(name):
        return Verdict(name, "-", ok=False, reason=reason)
    if name in EXCEPTIONS:
        return Verdict(name, "exception", ok=True, reason=EXCEPTIONS[name])
    licence = licence_of(dist)
    if licence is None:
        return Verdict(name, "unknown", ok=False, reason="licence metadata not recognised")
    if not spdx_allowed(licence):
        return Verdict(name, licence, ok=False, reason="licence not on the allowlist")
    return Verdict(name, licence, ok=True)


def locked_names(lock_text: str) -> list[str]:
    """Package names listed in a uv lockfile."""
    lock = tomllib.loads(lock_text)
    return sorted({normalise_name(p["name"]) for p in lock.get("package", [])})


def check_lock(lock_text: str) -> list[Verdict]:
    """Scope verdicts for every package in a uv lockfile (licences need installed metadata)."""
    verdicts = []
    for name in locked_names(lock_text):
        reason = scope_violation(name)
        verdicts.append(Verdict(name, "-", ok=reason is None, reason=reason or ""))
    return verdicts


def report(verdicts: list[Verdict], *, verbose: bool) -> int:
    """Print verdicts and return the process exit code."""
    failures = [v for v in verdicts if not v.ok]
    for v in verdicts if verbose else failures:
        mark = "ok  " if v.ok else "FAIL"
        note = f"  ({v.reason})" if v.reason else ""
        print(f"{mark} {v.name:<32} {v.licence}{note}")
    print(f"{len(verdicts)} distributions checked, {len(failures)} violations.")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    """Run the check selected on the command line."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--lock", action="store_true", help="check uv.lock names only")
    parser.add_argument("--verbose", action="store_true", help="list passing packages too")
    args = parser.parse_args(argv)
    if args.lock:
        verdicts = check_lock(LOCKFILE.read_text(encoding="utf-8"))
    else:
        verdicts = sorted((check(d) for d in distributions()), key=lambda v: v.name)
    return report(verdicts, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
