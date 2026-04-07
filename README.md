# MTPuTTY to MobaXterm Converter

Convert MTPuTTY XML session trees into MobaXterm bookmark files (`.mxtsessions`) while preserving folder structure, usernames, ports, and stored password fields.

## What this project contains

- `mtputty2mobaxterm.py`: Main converter script (interactive CLI + reusable functions)
- `test_conversion.py`: Minimal test runner using a sample XML file
- Sample input/output files for validation:
   - `mputty_tree_cyberark_26Jul2024_with_test.xml`
   - `test_output_latest.mxtsessions`
   - `MobaXterm_Sessions_(Latest_Model).mxtsessions`

## Features

- Converts MTPuTTY `Node` trees into MobaXterm `[Bookmarks]` sections
- Preserves nested folder hierarchy (`/` in input is written as `\` in MobaXterm `SubRep`)
- Supports direct and multi-hop/CyberArk-style connection strings
- Carries password values through as-is (no decryption/re-encryption)
- Auto-fixes invalid port `0` to `22`
- Prints conversion summary:
   - total sessions
   - sessions with passwords
   - folder-wise session counts

## Requirements

- Python 3.8+
- Standard library only (no third-party dependencies)

## Input assumptions

The converter expects MTPuTTY-style XML where sessions/folders are represented as `Node` elements:

- Folder: `Node` with `Type="0"`
- Session: `Node` with `Type="1"`

It first looks for `.//Putty`. If not found, it attempts parsing from the XML root.

## Connection parsing behavior

For each session, host/username are derived with this priority:

1. `CLParams` (except values starting with account-style prefixes like `ACCOUNT_ID@`)
2. `ServerName`
3. `UserName` field (for username fallback)

### Host extraction

- `CLParams` like `192.0.2.10 -l user_a -pw *****` -> host is first token (`192.0.2.10`)
- `ServerName` like `ACCOUNT_ID@jump_user@192.0.2.20@198.51.100.30` -> host is 3rd token (`192.0.2.20`)
- `ServerName` like `user@host` -> host is second token
- Otherwise, `ServerName` is used directly

### Username extraction

- If `CLParams` contains `-l <username>`, that value is used
- Else if `UserName` exists, it is used
- Else parsed from `ServerName` (`user@host` or second token in multi-hop form)

## Usage

Run interactive converter:

```bash
python3 mtputty2mobaxterm.py
```

Then provide the XML path when prompted:

```text
Please enter the path to your MTPuTTY XML file: /path/to/file.xml
```

Output is generated in the same directory as input using:

```text
<input_basename>_converted.mxtsessions
```

## Programmatic usage

You can call the converter directly from Python:

```python
from mtputty2mobaxterm import convert_mtputty_to_mobaxterm

convert_mtputty_to_mobaxterm(
      "mputty_tree_cyberark_26Jul2024_with_test.xml",
      "test_output_latest.mxtsessions"
)
```

## Run included test script

```bash
python3 test_conversion.py
```

This uses:

- input: `mputty_tree_cyberark_26Jul2024_with_test.xml`
- output: `test_output_latest.mxtsessions`

## MobaXterm import steps

1. Open MobaXterm
2. Go to `Settings -> Configuration -> Bookmark settings`
3. Click `Import bookmarks from file`
4. Select generated `.mxtsessions` file

## Notes and limitations

- The script is currently interactive (no CLI flags like `--input`/`--output`)
- Passwords are copied exactly from source fields; cryptographic transformation is not performed
- Session scripts (`<Script>`) are parsed but not written into `.mxtsessions`
- Parsing logic is tuned for the XML formats present in this repository (including CyberArk-like naming)
