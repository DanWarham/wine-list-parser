# Legacy Database Files

This folder contains the original database files that were replaced by enhanced versions.

## Files Moved Here:

### 1. `geo_hierarchy.json` (46KB, 2243 lines)
**Replaced by**: `enhanced_geo_hierarchy.json` (47KB, 2263 lines)
**Improvements**: Added German Mosel subregions, Spanish Rioja subregions, South African regions, fixed encoding issues

### 2. `grape_varieties.json` (7.4KB, 452 lines)  
**Replaced by**: `enhanced_grape_varieties.json` (7.9KB, 474 lines)
**Improvements**: Added Spanish Rías Baixas, Portuguese Dão, German/Austrian/Hungarian varieties, enhanced synonyms, better structure

### 3. `producer_locations.json` (8.2MB)
**Replaced by**: `enhanced_producer_locations.json` (7.8MB)
**Note**: This file was moved but the enhanced version is smaller, suggesting potential data loss. The enhanced version is being used with caution.

## Migration Date
August 7, 2025

## Reason for Migration
The enhanced files provide better coverage, more accurate data, and improved structure while maintaining backward compatibility through fallback mechanisms in the database manager. 