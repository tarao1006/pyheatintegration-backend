import base64
import io

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from pyheatintegration import PinchAnalyzer, Stream, extract_x, y_range
from pyheatintegration.line import Line


class Analyzer(PinchAnalyzer):

    def __init__(self, streams: list[Stream], minimum_temp_diff: float):
        super().__init__(streams, minimum_temp_diff)

    def create_grand_composite_curve(self) -> bytes:
        b = io.BytesIO()

        gcc_heats, gcc_temps = super().create_grand_composite_curve()

        fig, ax = plt.subplots(1, 1)
        ax.set_xlabel("Q [kW]")
        ax.set_ylabel("Shifted Temperature [℃]")
        ax.plot(gcc_heats, gcc_temps)
        fig.savefig(b, format="png")

        return b.getbuffer()

    def draw(self, hot_lines: list[Line], cold_lines: list[Line], with_vlines = False) -> bytes:
        b = io.BytesIO()

        fig, ax = plt.subplots(1, 1)
        ax.set_xlabel("Q [kW]")
        ax.set_ylabel("T [℃]")
        ax.add_collection(LineCollection(hot_lines, colors='#ff7f0e'))
        ax.add_collection(LineCollection(cold_lines, colors='#1f77b4'))
        if with_vlines:
            ymin, ymax = y_range(hot_lines + cold_lines)
            heats = extract_x(hot_lines + cold_lines)
            ax.vlines(heats, ymin=ymin, ymax=ymax, linestyles=':', colors='k')
        ax.autoscale()
        fig.savefig(b, format="png")

        return b.getbuffer()

    def create_tq(self, with_vlines = False) -> tuple[list[Line], list[Line], bytes]:
        hot_lines, cold_lines = super().create_tq()
        return hot_lines, cold_lines, self.draw(hot_lines, cold_lines, with_vlines)

    def create_tq_separated(self, with_vlines = False) -> tuple[list[Line], list[Line], bytes]:
        hot_lines, cold_lines = super().create_tq_separated()
        return hot_lines, cold_lines, self.draw(hot_lines, cold_lines, with_vlines)

    def create_tq_split(self, with_vlines = False) -> tuple[list[Line], list[Line], bytes]:
        hot_lines, cold_lines = super().create_tq_split()
        return hot_lines, cold_lines, self.draw(hot_lines, cold_lines, with_vlines)

    def create_tq_merged(self, with_vlines = False) -> tuple[list[Line], list[Line], bytes]:
        hot_lines, cold_lines = super().create_tq_merged()
        return hot_lines, cold_lines, self.draw(hot_lines, cold_lines, with_vlines)
