from typing import List, Dict, Any

import seaborn as sns
from contect.available.available import AvailableColorPalettes


def get_color_to_events_assignment(event_ids: List[str]) -> Dict[str, Any]:
    colors = sns.color_palette(AvailableColorPalettes.BLIND.value, len(event_ids)).as_hex()
    return dict(zip(event_ids, colors))
