# `training_script/build_ar_r2511_dataset.py`

[Open source](../training_script/build_ar_r2511_dataset.py)

## Purpose

Builds instruction/input/output examples grounded in AUTOSAR Classic Platform R25-11 ECUC definitions. It reads an ARXML member from a ZIP archive and can supplement ECUC parameter examples with matching PDF specification evidence.

## Data produced

The default output is `data/AR_R2511_train.json`. Records cover parameter definitions, references, containers, parent/choice relationships, and optional normative PDF excerpts. The writer validates the generated JSON records before replacing the destination file.

## Run

```powershell
python training_script/build_ar_r2511_dataset.py --help
python training_script/build_ar_r2511_dataset.py --no-pdfs
```

The source archive, PDF root, and output path can be overridden with CLI arguments. PDF extraction requires `pypdf`.