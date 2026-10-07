# `training_script/prepare_c_dataset.py`

[Open source](../training_script/prepare_c_dataset.py)

## Purpose

Packages the contents of a directory into a LLaMA-Factory Alpaca-format JSON dataset record. Files are traversed recursively and embedded with their relative paths.

## Important behavior

The generated record places the collected source text in `input` and leaves `output` empty. This is a source-bundle preparation utility, not a supervised input/output example generator by itself. It currently reads every file under the selected directory rather than filtering only by C/C++ extension.

## Run

```powershell
python training_script/prepare_c_dataset.py --input path/to/source --output-file data/custom_dataset.json
```