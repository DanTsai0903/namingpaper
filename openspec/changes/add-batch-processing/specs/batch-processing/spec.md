## ADDED Requirements

### Requirement: Batch Directory Processing

The system SHALL provide a `batch` command that processes all PDF files in a specified directory.

#### Scenario: Process all PDFs in directory

- **WHEN** user runs `namingpaper batch /path/to/papers`
- **THEN** the system extracts metadata from all PDF files in that directory
- **AND** displays a preview table of all planned renames

#### Scenario: Recursive directory scanning

- **WHEN** user runs `namingpaper batch /path/to/papers --recursive`
- **THEN** the system scans the directory and all subdirectories for PDF files
- **AND** processes all found PDF files

#### Scenario: Filter by pattern

- **WHEN** user runs `namingpaper batch /path/to/papers --filter "2023*"`
- **THEN** the system only processes PDF files matching the glob pattern

### Requirement: Batch Preview and Confirmation

The system SHALL display an interactive preview of all planned rename operations before execution.

#### Scenario: Display preview table

- **WHEN** batch processing completes metadata extraction
- **THEN** the system displays a table showing:
  - Original filename
  - Planned new filename
  - Status (ok, collision, error)
  - Confidence score

#### Scenario: Interactive confirmation

- **WHEN** preview is displayed and `--execute` flag is provided
- **THEN** user is prompted to confirm: [A]ll, [S]kip all, or [I]nteractive
- **AND** in Interactive mode, user can approve/skip each file individually

#### Scenario: Non-interactive mode

- **WHEN** user provides `--yes` flag with `--execute`
- **THEN** all valid renames are executed without prompts

### Requirement: Custom Naming Templates

The system SHALL support custom filename templates using placeholders.

#### Scenario: Use custom template

- **WHEN** user runs `namingpaper batch /path --template "{authors} ({year}) {title}"`
- **THEN** filenames are generated using the specified template

#### Scenario: Template placeholders

- **WHEN** a template is specified
- **THEN** the following placeholders SHALL be supported:
  - `{authors}` - Comma-separated author surnames
  - `{year}` - Publication year
  - `{journal}` - Full journal name
  - `{journal_abbrev}` - Journal abbreviation
  - `{title}` - Paper title

#### Scenario: Preset templates

- **WHEN** user runs `namingpaper batch /path --template compact`
- **THEN** the system uses the predefined "compact" template
- **AND** available presets include: default, compact, full

### Requirement: Batch Progress Tracking

The system SHALL display progress information during batch processing.

#### Scenario: Show progress bar

- **WHEN** batch processing is running
- **THEN** a progress bar shows: current file, total files, percentage complete

#### Scenario: Summary report

- **WHEN** batch processing completes
- **THEN** the system displays a summary:
  - Total files processed
  - Successful renames
  - Skipped (collisions)
  - Errors

### Requirement: Batch Error Handling

The system SHALL handle errors gracefully without stopping the entire batch.

#### Scenario: Continue on error

- **WHEN** metadata extraction fails for one file
- **THEN** the system logs the error
- **AND** continues processing remaining files
- **AND** includes the failed file in the final summary

#### Scenario: Collision handling

- **WHEN** multiple source files would result in the same destination name
- **THEN** the system detects the collision during preview
- **AND** marks affected files with "collision" status
- **AND** applies the configured collision strategy (skip/increment)
