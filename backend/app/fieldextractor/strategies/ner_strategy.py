import spacy
from typing import Dict, Any, Tuple, List
import re

class NERStrategy:
    def __init__(self):
        # Load the English language model
        self.nlp = spacy.load('en_core_web_sm')
        
        # Define entity mappings with confidence weights
        self.entity_mapping = {
            'ORG': {
                'fields': ['producer_name', 'producer_title'],
                'weight': 0.9,
                'context_words': ['wine', 'vineyard', 'estate', 'cellar', 'chateau']
            },
            'GPE': {
                'fields': ['country', 'region', 'sub_region'],
                'weight': 0.8,
                'context_words': ['from', 'of', 'in', 'region', 'appellation']
            },
            'PRODUCT': {
                'fields': ['wine_name', 'type', 'sub_type'],
                'weight': 0.7,
                'context_words': ['wine', 'blend', 'cuvee', 'reserve']
            },
            'WORK_OF_ART': {
                'fields': ['wine_name'],
                'weight': 0.6,
                'context_words': ['named', 'called', 'titled']
            },
            'PERCENT': {
                'fields': ['price'],
                'weight': 0.9,
                'context_words': ['price', 'cost', '£', '$', '€']
            },
            'DATE': {
                'fields': ['vintage'],
                'weight': 0.9,
                'context_words': ['vintage', 'year', 'harvest']
            },
            'MISC': {
                'fields': ['designation', 'classification', 'colour', 'grape_variety'],
                'weight': 0.7,
                'context_words': ['type', 'style', 'grape', 'variety', 'color']
            }
        }

    def _get_context_score(self, text: str, entity: spacy.tokens.Span, context_words: List[str]) -> float:
        """Calculate a context score based on nearby words."""
        # Get words before and after the entity
        start = max(0, entity.start_char - 50)
        end = min(len(text), entity.end_char + 50)
        context = text[start:end].lower()
        
        # Count matching context words
        matches = sum(1 for word in context_words if word.lower() in context)
        return min(1.0, matches / len(context_words)) if context_words else 0.5

    def _extract_grape_varieties(self, text: str) -> List[str]:
        """Extract grape varieties using a combination of NER and regex."""
        common_grapes = [
            'Chardonnay', 'Cabernet Sauvignon', 'Merlot', 'Pinot Noir', 'Syrah',
            'Sauvignon Blanc', 'Riesling', 'Malbec', 'Grenache', 'Tempranillo',
            'Nebbiolo', 'Sangiovese', 'Zinfandel', 'Chenin Blanc', 'Viognier'
        ]
        
        # Create a pattern that matches grape names
        grape_pattern = r'\b(' + '|'.join(common_grapes) + r')\b'
        return re.findall(grape_pattern, text, re.IGNORECASE)

    def extract(self, block: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        text = block.get('text', '')
        doc = self.nlp(text)
        extracted_fields = {}
        total_entities = 0
        matched_entities = 0
        total_confidence = 0.0

        # Process named entities
        for ent in doc.ents:
            total_entities += 1
            if ent.label_ in self.entity_mapping:
                matched_entities += 1
                mapping = self.entity_mapping[ent.label_]
                
                # Calculate confidence based on entity type and context
                context_score = self._get_context_score(text, ent, mapping['context_words'])
                confidence = mapping['weight'] * context_score
                total_confidence += confidence

                # Map the entity to our field names
                for field in mapping['fields']:
                    if field not in extracted_fields or confidence > extracted_fields[field]['confidence']:
                        extracted_fields[field] = {
                            'value': ent.text,
                            'confidence': confidence,
                            'provenance': 'ner'
                        }

        # Extract grape varieties
        grape_varieties = self._extract_grape_varieties(text)
        if grape_varieties:
            extracted_fields['grape_variety'] = {
                'value': ', '.join(grape_varieties),
                'confidence': 0.8,
                'provenance': 'ner+regex'
            }

        # Calculate overall confidence
        confidence = total_confidence / total_entities if total_entities > 0 else 0.0
        return extracted_fields, confidence
