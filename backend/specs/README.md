# Specs Directory

This directory contains specifications, reference data, and processing outputs for the wine list parser system.

## Directory Structure

```
specs/
├── LWINdatabase.xlsx          # LWIN database reference file
├── processing-outputs/        # Processing stage outputs (for development/debugging)
│   ├── extractor/            # Text extraction outputs
│   ├── preprocessor/         # Text preprocessing outputs
│   ├── categorizer/          # Block categorization outputs
│   ├── field_extractor/      # Field extraction outputs
│   └── learning/             # Rule learning outputs
├── test-data/                # Test PDFs and expected outputs
│   ├── realworld/           # Real-world wine list examples
│   └── generated/           # Generated test cases
└── rules/                   # Rule templates and examples
    ├── templates/           # Rule templates for different restaurants
    └── examples/            # Example rule configurations
```

## Data Management

### Production Data Storage
- **Supabase Storage**: All processing data is stored in Supabase Storage under `processing-data/{wine_list_id}/{stage}/`
- **Automatic Cleanup**: When wine lists are deleted, all associated processing data is automatically removed
- **Versioning**: Multiple versions of processing outputs can be stored with version identifiers

### Development/Testing Data
- **Local Storage**: Test outputs can be saved locally in `specs/processing-outputs/` for development
- **Reference Data**: Expected outputs and test cases stored in `specs/test-data/`
- **Rule Templates**: Reusable rule configurations in `specs/rules/`

## Processing Stages

1. **extractor**: Raw text extraction from PDF
2. **preprocessor**: Text cleaning and normalization
3. **categorizer**: Block categorization (wine, header, etc.)
4. **field_extractor**: Field extraction using various strategies
5. **learning**: Rule learning and refinement results

## API Endpoints

- `GET /wine-lists/{file_id}/processing-data` - List all processing stages
- `GET /wine-lists/{file_id}/processing-data?stage={stage}` - Get specific stage data
- `GET /wine-lists/{file_id}/processing-data?stage={stage}&version={version}` - Get specific version

## Migration from Test-Based Storage

The system has been migrated from storing JSON outputs in test fixtures to a professional storage structure:

### Before (Test-Based)
```
tests/test_pdf_processing/fixtures/realworld/Sager_and_Wilde_Test1/
├── extractor_output.json
├── preprocessor_output.json
├── categorizer_output.json
└── field_extractor_output.json
```

### After (Production-Ready)
```
Supabase Storage: processing-data/{wine_list_id}/
├── extractor/
│   └── extractor_20241201_143022.json
├── preprocessor/
│   └── preprocessor_20241201_143025.json
├── categorizer/
│   └── categorizer_20241201_143030.json
└── field_extractor/
    ├── field_extractor_20241201_143035.json
    └── field_extractor_vreparsed_20241201_143040.json
```

## Benefits of New Structure

1. **Automatic Cleanup**: Data is automatically removed when wine lists are deleted
2. **Versioning**: Multiple processing attempts can be tracked
3. **Scalability**: Cloud storage handles large datasets
4. **Organization**: Clear separation by wine list and processing stage
5. **API Access**: Processing data can be retrieved via API
6. **Production Ready**: Suitable for production deployment 