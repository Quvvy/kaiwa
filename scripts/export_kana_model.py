"""Build the kana model used by kaiwa.course.kana_judge (one-off, ~2 GB download).

Needs torch + transformers + onnx, which Kaiwa itself does not, so run it from a
throwaway venv:

    python -m venv kana-venv
    kana-venv/Scripts/pip install torch --index-url https://download.pytorch.org/whl/cpu
    kana-venv/Scripts/pip install transformers onnx onnxruntime
    kana-venv/Scripts/python scripts/export_kana_model.py

Writes model.onnx (~355 MB; only MatMuls int8-quantized — quantized convolutions
are 7x slower on CPU) and vocab.json to %LOCALAPPDATA%/Kaiwa/models/kana-ctc.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForCTC, AutoProcessor

NAME = "vumichien/wav2vec2-large-xlsr-japanese-hiragana"


def main() -> None:
    root = Path(os.environ.get("KAIWA_DATA_DIR") or Path(os.environ["LOCALAPPDATA"]) / "Kaiwa")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "models" / "kana-ctc"
    out.mkdir(parents=True, exist_ok=True)
    proc = AutoProcessor.from_pretrained(NAME)
    model = AutoModelForCTC.from_pretrained(NAME).eval()
    with tempfile.TemporaryDirectory() as tmp:
        fp32 = Path(tmp) / "fp32.onnx"
        torch.onnx.export(
            model, (torch.zeros(1, 16000),), str(fp32),
            input_names=["audio"], output_names=["logits"],
            dynamic_axes={"audio": {1: "n"}, "logits": {1: "t"}},
            opset_version=17, dynamo=False,
        )
        quantize_dynamic(str(fp32), str(out / "model.onnx"), weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul"])
    meta = {
        "vocab": proc.tokenizer.get_vocab(),
        "blank": proc.tokenizer.pad_token_id,
        "normalize": bool(proc.feature_extractor.do_normalize),
        "source": NAME,
    }
    (out / "vocab.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
