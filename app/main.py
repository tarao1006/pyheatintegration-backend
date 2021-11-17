import base64
import io
import json
import time
import zipfile

import pandas as pd
from fastapi import Body, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyheatintegration import (PinchAnalyzer, PyHeatIntegrationError, Stream,
                               StreamState, StreamType,
                               get_possible_minimum_temp_diff_range)

from .analyzer import Analyzer

app = FastAPI()

origins = [
    'http://localhost:3000',
    'https://pyheatintegration.vercel.app',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StreamModel(BaseModel):
    id: str
    inputTemperature: float
    outputTemperature: float
    heatLoad: float
    type: int
    state: int
    cost: float = 0.0
    reboilerOrReactor: bool = False

    def convert(self) -> Stream:
        return Stream(
            id_=self.id,
            input_temperature=self.inputTemperature,
            output_temperature=self.outputTemperature,
            heat_load=self.heatLoad,
            type_=StreamType(self.type),
            state=StreamState(self.state),
            cost=self.cost,
            reboiler_or_reactor=self.reboilerOrReactor
        )


class Streams(BaseModel):
    streams: list[StreamModel]


@app.get("/")
def root():
    return {"message": "Hello, world."}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    time.sleep(1)
    data = json.loads(file.file.read())
    df = pd.DataFrame(data['streams'])

    try:
        streams = [
            Stream(
                row.inputTemperature,
                row.outputTemperature,
                row.heatLoad,
                StreamType(row.type),
                StreamState(row.state),
                row.cost,
                row.reboilerOrReactor,
                row.id
            ) for row in df.itertuples()
        ]
    except PyHeatIntegrationError as e:
        return {
            "succeeded": False,
            "message": str(e),
        }

    if message := PinchAnalyzer.validate_streams(streams):
        return {
            "succeeded": False,
            "message": message,
        }

    possible_minimum_temp_diff_range = get_possible_minimum_temp_diff_range(streams)

    return {
        "succeeded": True,
        "minimumTempDiffRange": {
            "min": possible_minimum_temp_diff_range.start,
            "max": possible_minimum_temp_diff_range.finish,
        },
        "streams": json.loads(df.to_json(orient='records', force_ascii=False)),
    }


@app.post("/validate")
async def validate(streams: Streams):
    time.sleep(1)

    try:
        streams_ = [stream.convert() for stream in streams.streams]
    except PyHeatIntegrationError as e:
        return {
            "succeeded": False,
            "message": str(e),
        }

    if message := PinchAnalyzer.validate_streams(streams_):
        return {
            "succeeded": False,
            "message": message,
        }

    possible_minimum_temp_diff_range = get_possible_minimum_temp_diff_range(streams_)

    return {
        "succeeded": True,
        "minimumTempDiffRange": {
            "min": possible_minimum_temp_diff_range.start,
            "max": possible_minimum_temp_diff_range.finish,
        },
    }


@app.post("/run")
async def run(streams: list[StreamModel], minimumTempDiff: float = Body(...)):
    """Entry point to draw graph.py"""
    minimum_temp_diff = minimumTempDiff

    try:
        analyzer = Analyzer([stream.convert() for stream in streams], minimum_temp_diff)

        buf_gcc = analyzer.create_grand_composite_curve()

        hot_lines, cold_lines, buf_tq = analyzer.create_tq()
        _, _, buf_tq_with_vlines = analyzer.create_tq(True)

        hot_lines_separated, cold_lines_separated, buf_tq_separated = analyzer.create_tq_separated()
        _, _, buf_tq_separated_with_vlines = analyzer.create_tq_separated(True)

        hot_lines_split, cold_lines_split, buf_tq_split = analyzer.create_tq_split()
        _, _, buf_tq_split_with_vlines = analyzer.create_tq_split(True)

        hot_lines_merged, cold_lines_merged, buf_tq_merged = analyzer.create_tq_merged()
        _, _, buf_tq_merged_with_vlines = analyzer.create_tq_merged(True)

        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as myzip:
            myzip.writestr("gcc.png", buf_gcc)

            myzip.writestr("tq.png", buf_tq)
            myzip.writestr("tq_with_vlines.png", buf_tq_with_vlines)
            myzip.writestr("tq.json", json.dumps({"hot_lines": hot_lines, "cold_lines": cold_lines}, indent=2))

            myzip.writestr("tq_separated.png", buf_tq_separated)
            myzip.writestr("tq_separated_with_vlines.png", buf_tq_separated_with_vlines)
            myzip.writestr("tq_separeted.json", json.dumps({"hot_lines": hot_lines_separated, "cold_lines": cold_lines_separated}, indent=2))

            myzip.writestr("tq_split.png", buf_tq_split)
            myzip.writestr("tq_split_with_vlines.png", buf_tq_split_with_vlines)
            myzip.writestr("tq_split.json", json.dumps({"hot_lines": hot_lines_split, "cold_lines": cold_lines_split}, indent=2))

            myzip.writestr("tq_merged.png", buf_tq_merged)
            myzip.writestr("tq_merged_with_vlines.png", buf_tq_merged_with_vlines)
            myzip.writestr("tq_merged.json", json.dumps({"hot_lines": hot_lines_merged, "cold_lines": cold_lines_merged}, indent=2))

        b.seek(0)

        return {
            "succeeded": True,
            "zip": base64.b64encode(b.getvalue()).decode(),
            "images": {
                "gcc": base64.b64encode(buf_gcc).decode(),
                "tq": base64.b64encode(buf_tq).decode(),
                "tq_with_vlines": base64.b64encode(buf_tq_with_vlines).decode(),
                "tq_separated": base64.b64encode(buf_tq_separated).decode(),
                "tq_separated_with_vlines": base64.b64encode(buf_tq_separated_with_vlines).decode(),
                "tq_split": base64.b64encode(buf_tq_split).decode(),
                "tq_split_with_vlines": base64.b64encode(buf_tq_split_with_vlines).decode(),
                "tq_merged": base64.b64encode(buf_tq_merged).decode(),
                "tq_merged_with_vlines": base64.b64encode(buf_tq_merged_with_vlines).decode(),
            },
        }
    except PyHeatIntegrationError as e:
        return {
            "succeeded": False,
            "message": str(e),
            "critical": False,
        }
    except Exception as e:
        return {
            "succeeded": False,
            "message": str(e),
            "critical": True,
        }
