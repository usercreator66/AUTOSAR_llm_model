# `training_script/merge_all_loras.py`

[Open source](../training_script/merge_all_loras.py)

## Purpose

Discovers adapter directories containing `adapter_config.json` under the configured LoRA save root, then merges them successively with PEFT onto the configured base model.

## Inputs and output

Defaults point to `models/Qwen3.5-9B` and `saves/Qwen3.5-9B-Thinking/lora`; output is `merged_autosar_lora` below the LoRA root. `discover_adapters()` lists eligible adapters, while `merge_all_loras()` performs the model operation.

## Caution

If the output directory already exists, the script deletes it before starting the merge. Verify the configured paths and back up anything needed before running `python training_script/merge_all_loras.py`. The script requires Torch, Transformers, and PEFT, and model merging can require substantial memory.