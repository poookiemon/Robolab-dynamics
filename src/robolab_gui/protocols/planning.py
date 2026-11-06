"""Protocol planning and weighted baseline execution time estimation."""

from typing import List, Dict, Any, Union
from robolab_gui.protocols.models import Protocol, ProtocolStep


class ProtocolPlanner:
    @classmethod
    def estimate_step_durations(
        cls,
        steps: Union[List[ProtocolStep], List[Dict[str, Any]]],
        xy_speed_mm_s: float = 200.0,
        lld_enabled: bool = True,
    ) -> List[float]:
        durations: List[float] = []

        for item in steps:
            if isinstance(item, ProtocolStep):
                s = item.to_dict()
            else:
                s = item

            action = s.get("action", "")
            vol = float(s.get("volume", 0.0) or 0.0)
            mix_cycles = int(s.get("mix_cycles", 0) or 0)

            if "Incubate" in action:
                durations.append(max(0.0, vol))
                continue
            elif "FOC48" in action:
                durations.append(150.0)
                continue
            elif "Data Analysis" in action:
                durations.append(5.0)
                continue

            travel_time = 0.8
            is_8ch = bool(s.get("eight_ch_symmetric") or (str(s.get("mounted_channels", "")).count("-") > 0))
            act_lower = action.lower()

            if "pick" in act_lower and "tip" in act_lower:
                step_t = travel_time + 3.5
            elif "discard" in act_lower or "drop" in act_lower:
                step_t = travel_time + 3.2
            elif "aspirate" in act_lower:
                draw_time = max(0.8, vol * 0.005)
                step_t = travel_time + 8.3 + draw_time
            elif "dispense" in act_lower:
                disp_time = max(0.6, vol * 0.004)
                mix_time = mix_cycles * 4.7
                step_t = travel_time + 8.0 + disp_time + mix_time
            elif "mix" in act_lower:
                step_t = travel_time + 4.0 + (mix_cycles * 4.7)
            else:
                step_t = travel_time + 2.0

            durations.append(round(step_t, 2))

        return durations

    @classmethod
    def estimate_total_duration(cls, protocol: Union[Protocol, List[ProtocolStep], List[Dict[str, Any]]]) -> float:
        if isinstance(protocol, Protocol):
            steps = protocol.steps
        else:
            steps = protocol
        durations = cls.estimate_step_durations(steps)
        return round(sum(durations), 1)

    @staticmethod
    def format_duration(seconds: float) -> str:
        s = max(0, int(seconds))
        hours = s // 3600
        minutes = (s % 3600) // 60
        secs = s % 60
        return f"{hours:02d}h {minutes:02d}m {secs:02d}s"
