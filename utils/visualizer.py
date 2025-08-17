"""Text span visualization utilities."""

import html
from typing import Dict, List, Tuple
from .colors import get_concept_colors, rgba_from_hex, get_model_version_opacity


class SpanHighlighter:
    """Handles highlighting of text spans with different colors and opacities."""
    
    def __init__(self):
        self.concept_colors = {}
        self.model_version_counts = {}
    
    def _prepare_colors(self, concept_spans: Dict[str, List[Tuple[int, int]]]):
        """Prepare color mappings for concepts and model versions."""
        # Extract unique concepts
        concepts = set()
        for key in concept_spans.keys():
            concept_id = key.split('_')[0]
            concepts.add(concept_id)
        
        # Generate colors for concepts
        self.concept_colors = get_concept_colors(list(concepts))
        
        # Count model versions per concept for opacity calculation
        self.model_version_counts = {}
        for concept in concepts:
            versions = [key for key in concept_spans.keys() if key.startswith(f"{concept}_")]
            self.model_version_counts[concept] = len(versions)
    
    def _get_span_style(self, concept_model_key: str, version_index: int) -> str:
        """Get CSS style for a span."""
        concept_id = concept_model_key.split('_')[0]
        base_color = self.concept_colors[concept_id]
        opacity = get_model_version_opacity(version_index, self.model_version_counts[concept_id])
        color = rgba_from_hex(base_color, opacity)
        
        return f"background-color: {color}; padding: 1px 3px;"
    
    def _create_overlapping_spans(self, text: str, concept_spans: Dict[str, List[Tuple[int, int]]]) -> str:
        """Create highlighted text handling overlapping spans."""
        # Create a list of all span events (start/end)
        events = []
        
        for concept_model_key, spans in concept_spans.items():
            for start, end in spans:
                events.append((start, 'start', concept_model_key))
                events.append((end, 'end', concept_model_key))
        
        # Sort events by position, with end events before start events at same position
        events.sort(key=lambda x: (x[0], x[1] == 'start'))
        
        # Build highlighted HTML
        result = []
        active_spans = []
        last_pos = 0
        
        for pos, event_type, concept_model_key in events:
            # Add text before this position
            if pos > last_pos:
                text_chunk = html.escape(text[last_pos:pos])
                if active_spans:
                    # Apply styling for currently active spans
                    # Use the most recent span for styling (simple approach)
                    latest_span = active_spans[-1]
                    concept_id = latest_span.split('_')[0]
                    version_index = len([s for s in active_spans if s.startswith(f"{concept_id}_")]) - 1
                    style = self._get_span_style(latest_span, version_index)
                    result.append(f'<span style="{style}" title="{latest_span}">{text_chunk}</span>')
                else:
                    result.append(text_chunk)
            
            # Handle event
            if event_type == 'start':
                active_spans.append(concept_model_key)
            else:  # end
                if concept_model_key in active_spans:
                    active_spans.remove(concept_model_key)
            
            last_pos = pos
        
        # Add remaining text
        if last_pos < len(text):
            text_chunk = html.escape(text[last_pos:])
            result.append(text_chunk)
        
        return ''.join(result)
    
    def highlight_text(self, text: str, concept_spans: Dict[str, List[Tuple[int, int]]]) -> str:
        """Generate HTML with highlighted concept spans."""
        if not concept_spans:
            return html.escape(text)
        
        self._prepare_colors(concept_spans)
        return self._create_overlapping_spans(text, concept_spans)
    
    def get_legend_html(self, concept_spans: Dict[str, List[Tuple[int, int]]]) -> str:
        """Generate HTML legend for the highlighting."""
        if not concept_spans:
            return ""
        
        self._prepare_colors(concept_spans)
        
        legend_items = []
        for concept_model_key in sorted(concept_spans.keys()):
            concept_id, model_version = concept_model_key.split('_', 1)
            version_index = len([k for k in concept_spans.keys() 
                               if k.startswith(f"{concept_id}_") and k <= concept_model_key]) - 1
            style = self._get_span_style(concept_model_key, version_index)
            span_count = len(concept_spans[concept_model_key])
            
            legend_items.append(f'''<span style="{style.strip()}; margin-right: 8px;">{concept_id.upper()}</span> <small>{model_version} ({span_count} span{'' if span_count == 1 else 's'})</small><br>''')
        
        return f'''<div style="margin: 1.5rem 0; font-size: 0.9rem; color: #666;"><strong>Legend:</strong> {''.join(legend_items)}</div>'''


def create_highlighted_passage(text: str, concept_spans: Dict[str, List[Tuple[int, int]]]) -> Tuple[str, str]:
    """Create highlighted passage HTML and legend."""
    highlighter = SpanHighlighter()
    highlighted_text = highlighter.highlight_text(text, concept_spans)
    legend_html = highlighter.get_legend_html(concept_spans)
    return highlighted_text, legend_html