"""Color scheme management for concept visualization."""

import colorsys
from typing import Dict, List, Tuple


def generate_distinct_colors(n: int) -> List[str]:
    """Generate n visually distinct colors in hex format."""
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.7
        lightness = 0.6
        rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
        )
        colors.append(hex_color)
    return colors


def get_concept_colors(concept_ids: List[str]) -> Dict[str, str]:
    """Get color mapping for concept IDs."""
    colors = generate_distinct_colors(len(concept_ids))
    return dict(zip(concept_ids, colors))


def get_model_version_opacity(version_index: int, total_versions: int) -> float:
    """Get opacity for model version (darker = newer/higher priority)."""
    if total_versions == 1:
        return 1.0
    return 0.4 + (0.6 * version_index / (total_versions - 1))


def rgba_from_hex(hex_color: str, opacity: float) -> str:
    """Convert hex color to rgba with given opacity."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {opacity})"