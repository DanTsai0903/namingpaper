## 1. Core Batch Processing

- [x] 1.1 Create `batch.py` module with `BatchProcessor` class
- [x] 1.2 Implement directory scanning with glob patterns
- [x] 1.3 Add parallel/sequential extraction options
- [x] 1.4 Implement progress tracking for batch operations

## 2. CLI Integration

- [x] 2.1 Add `batch` command to CLI with directory argument
- [x] 2.2 Add `--recursive` flag for subdirectory scanning
- [x] 2.3 Add `--filter` option for filename pattern matching
- [x] 2.4 Add `--parallel` option to control concurrent processing
- [x] 2.5 Add `--template` option for custom naming format

## 3. Interactive Preview

- [x] 3.1 Create rich table showing all planned renames
- [x] 3.2 Add color-coded status (ok, collision, error)
- [x] 3.3 Implement interactive confirmation (all/skip/select)
- [x] 3.4 Add `--json` output option for scripting

## 4. Template System

- [x] 4.1 Define template syntax with placeholders ({authors}, {year}, {journal}, {title})
- [x] 4.2 Add template parsing and validation
- [x] 4.3 Implement template-based filename generation
- [x] 4.4 Add preset templates (default, compact, full)

## 5. Testing

- [x] 5.1 Unit tests for BatchProcessor
- [x] 5.2 Unit tests for template parsing
- [x] 5.3 Integration tests for batch CLI command
- [x] 5.4 Test collision handling across batch
