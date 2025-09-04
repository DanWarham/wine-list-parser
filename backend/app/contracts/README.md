# Contracts Package

This package provides the core interfaces and contracts that ensure consistent behavior across all application components.

## 📁 Package Structure

```
contracts/
├── __init__.py          # Main package exports
├── base.py              # Base service contracts
├── extraction.py        # Extraction strategy contracts
├── confidence.py        # Confidence calculation contracts
├── processing.py        # Processing pipeline contracts
└── README.md            # This documentation
```

## 🎯 Purpose

The contracts package establishes a **contract-first architecture** that:

1. **Ensures Consistency**: All services follow the same patterns
2. **Enables Testing**: Easy to mock and test individual components
3. **Promotes Modularity**: Clear separation of concerns
4. **Facilitates Extensibility**: Easy to add new implementations
5. **Supports the 3-Tier Confidence System**: Foundation for confidence calculation

## 🔧 Core Contracts

### Base Contracts (`base.py`)

#### `BaseService`
- **Purpose**: Foundation for all services
- **Key Methods**: `validate_input()`, `handle_error()`
- **Usage**: Inherit from this for all service implementations

#### `ServiceFactory`
- **Purpose**: Service instantiation and dependency injection
- **Key Methods**: `create_service()`, `get_service_dependencies()`
- **Usage**: Central point for service creation

#### `DataProcessor`
- **Purpose**: Generic data processing operations
- **Key Methods**: `process()`, `validate_result()`
- **Usage**: For any component that processes data

#### `Configurable`
- **Purpose**: Components that can be configured
- **Key Methods**: `update_config()`, `validate_config()`
- **Usage**: For components that need runtime configuration

#### `Auditable`
- **Purpose**: Operations that need audit trails
- **Key Methods**: `log_operation()`, `get_audit_trail()`
- **Usage**: For compliance and debugging

### Extraction Contracts (`extraction.py`)

#### `ExtractionStrategy`
- **Enum Values**: `DATABASE`, `NER`, `REGEX`, `AI`, `HYBRID`
- **Purpose**: Defines available extraction methods

#### `FieldExtractor`
- **Purpose**: Contract for all extraction strategies
- **Key Methods**: `extract()`, `get_supported_fields()`
- **Usage**: Implement for new extraction strategies

#### `ExtractionResult`
- **Purpose**: Standardized result structure
- **Fields**: `fields`, `confidence`, `strategy`, `metadata`
- **Usage**: Return type for all extraction operations

#### `ExtractionPipeline`
- **Purpose**: Orchestrates multiple extraction strategies
- **Key Methods**: `process()`, `merge_results()`
- **Usage**: Combine results from different strategies

### Confidence Contracts (`confidence.py`)

#### `ConfidenceTier`
- **Enum Values**: `HIGH` (0.8-1.0), `MEDIUM` (0.5-0.79), `LOW` (0.0-0.49)
- **Purpose**: 3-tier confidence classification system

#### `ConfidenceCalculator`
- **Purpose**: Calculate confidence scores
- **Key Methods**: `calculate_field_confidence()`, `calculate_overall_confidence()`
- **Usage**: Core of the confidence system

#### `FieldConfidence`
- **Purpose**: Confidence information for specific fields
- **Fields**: `value`, `confidence`, `strategy`, `tier`
- **Usage**: Track confidence per field

#### `ConfidenceThresholdManager`
- **Purpose**: Manage confidence thresholds dynamically
- **Key Methods**: `get_thresholds()`, `update_thresholds()`
- **Usage**: Adjust thresholds based on performance

### Processing Contracts (`processing.py`)

#### `ProcessingStage`
- **Enum Values**: `UPLOAD`, `EXTRACTION`, `PREPROCESSING`, etc.
- **Purpose**: Define processing pipeline stages

#### `PDFProcessor`
- **Purpose**: PDF file processing operations
- **Key Methods**: `process_pdf()`, `extract_text()`, `extract_metadata()`
- **Usage**: Handle PDF files consistently

#### `ProcessingPipeline`
- **Purpose**: Orchestrate complete processing workflow
- **Key Methods**: `process()`, `add_stage()`, `remove_stage()`
- **Usage**: Manage end-to-end processing

#### `ProcessingMonitor`
- **Purpose**: Track processing progress
- **Key Methods**: `start_monitoring()`, `update_progress()`
- **Usage**: Real-time processing status

## 🚀 Usage Examples

### Implementing a New Extraction Strategy

```python
from contracts.extraction import FieldExtractor, ExtractionStrategy, ExtractionResult

class MyCustomExtractor(FieldExtractor):
    def __init__(self):
        super().__init__()
        self.strategy_type = ExtractionStrategy.AI
    
    async def extract(self, text: str, context: Dict[str, Any] = None):
        # Your custom extraction logic here
        fields = {"producer": "Extracted Producer"}
        return ExtractionResult(
            fields=fields,
            confidence=0.85,
            strategy=self.strategy_type
        )
    
    async def get_supported_fields(self):
        return ["producer", "wine_name"]
    
    async def get_strategy_metadata(self):
        return {"type": "custom_ai", "version": "1.0"}
    
    async def validate_input(self, text: str):
        return len(text) > 0
```

### Using the Confidence System

```python
from contracts.confidence import ConfidenceCalculator, ConfidenceTier

class MyConfidenceCalculator(ConfidenceCalculator):
    async def calculate_field_confidence(self, field_data: Dict[str, Any], context: Dict[str, Any] = None):
        # Your confidence calculation logic
        base_confidence = field_data.get('confidence', 0.5)
        
        # Apply context adjustments
        if context and context.get('restaurant_id'):
            base_confidence *= 1.1  # Boost for known restaurants
        
        return min(base_confidence, 1.0)
    
    async def calculate_overall_confidence(self, field_confidences: Dict[str, float], context: Dict[str, Any] = None):
        if not field_confidences:
            return 0.0
        
        # Simple average for now
        return sum(field_confidences.values()) / len(field_confidences)
```

### Creating a Processing Pipeline

```python
from contracts.processing import ProcessingPipeline, ProcessingStage, ProcessingResult

class MyProcessingPipeline(ProcessingPipeline):
    async def process(self, input_data: Dict[str, Any], config: Dict[str, Any] = None):
        try:
            # Execute pipeline stages
            result = ProcessingResult(success=True, data={})
            
            # Add your processing logic here
            
            return result
        except Exception as e:
            return ProcessingResult(
                success=False,
                errors=[str(e)]
            )
```

## 🔗 Integration with Existing Services

The contracts are designed to integrate seamlessly with existing services:

1. **Update existing services** to inherit from appropriate contracts
2. **Implement missing methods** required by the contracts
3. **Use contract types** in method signatures and return types
4. **Leverage the confidence system** for better extraction quality

## 📊 Benefits

- **Reduced Duplication**: Common patterns defined once
- **Better Testing**: Easy to mock and test components
- **Improved Maintainability**: Clear interfaces and contracts
- **Enhanced Extensibility**: Easy to add new implementations
- **Consistent Behavior**: All components follow the same patterns
- **Foundation for Confidence System**: 3-tier confidence architecture

## 🎯 Next Steps

1. **Update existing services** to implement these contracts
2. **Implement the confidence system** using these contracts
3. **Add new extraction strategies** following the contracts
4. **Create processing pipelines** using the pipeline contracts
5. **Add comprehensive testing** for all contract implementations
