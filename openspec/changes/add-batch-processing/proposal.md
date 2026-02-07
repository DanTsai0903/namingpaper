# Change: Add Batch Processing Support

## Why

Currently the CLI only supports processing one PDF file at a time. Users with large paper collections need to run the command repeatedly for each file, which is tedious and time-consuming. Additionally, there's no way to preview all planned renames before executing them, or to apply different naming templates.

## What Changes

- Add a new `batch` command that processes all PDFs in a directory
- Support recursive directory scanning with `--recursive` flag
- Add interactive preview mode showing all planned renames in a table
- Allow users to confirm/skip individual files or proceed with all
- Support custom naming templates via `--template` option
- Add `--filter` option to process only files matching a pattern

## Impact

- Affected specs: New `batch-processing` capability
- Affected code:
  - `cli.py` - Add new `batch` command
  - New `batch.py` module for batch orchestration
  - `formatter.py` - Add template support for custom naming patterns
