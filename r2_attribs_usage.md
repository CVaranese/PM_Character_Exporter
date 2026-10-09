# r2_attribs Sheets Converter

Use `attribs_sheets.py` to convert `r2_attribs.txt` to a Google Sheets-friendly format and back.

## Export to Google Sheets

```powershell
python attribs_sheets.py to-sheets r2_attribs.txt r2_attribs.tsv
```

Open the `.tsv` file, copy its contents, and paste into Google Sheets. The sheet will have three columns: **Section**, **Key**, **Value**, with the section name only on the first row of each group.

Sub-keys (`ECBDimensions.X`, `EcbBones.EcbBones[0]`, etc.) are stripped — only the parent keys are shown.

## Import back from Google Sheets

Copy all cells from the sheet and paste into a `.tsv` file, then run:

```powershell
python attribs_sheets.py from-sheets r2_attribs.tsv r2_attribs.txt
```

Sub-keys are automatically rebuilt from whatever is in the compound parent value (e.g. `(X=80.000000,Y=170.000000)` regenerates `.X` and `.Y`).
