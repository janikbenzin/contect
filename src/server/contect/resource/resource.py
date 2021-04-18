import json
import os
from typing import Any, Dict
import pickle

import dask.dataframe as ddf
import pandas as pd
from contect.parsedata.objects.exporter.exporter import export_to_dataframe
from contect.parsedata.objects.oclog import ObjectCentricLog

project_root = os.environ.get('CONTECT_PATH')


def get_resource_pptpath(name: str) -> str:
    return f'{project_root}/src/res/powerpoint_tables/{name}.pptx'


def get_resource_figurepath(name: str) -> str:
    return f'{project_root}/src/res/evaluation_figures/{name}'


def get_resource_filepath(name: str) -> str:
    return f'{project_root}/src/res/{name}'


def get_resource_uploadpath(name: str) -> str:
    return f'{project_root}/src/res/uploads/{name}'


def read_csv_from_file(name: str, sep: str = ';', local: bool = True) -> ddf.DataFrame:
    if local:
        return ddf.read_csv(get_resource_filepath(name), sep=sep)
    else:
        return ddf.read_csv(get_resource_uploadpath(name), sep=sep)


def read_pd_from_csv_file(name: str, sep: str = ',') -> pd.DataFrame:
    return pd.read_csv(get_resource_filepath(name), sep=sep)


def read_json_from_file(name: str, local: bool = True) -> Dict:
    if local:
        with open(get_resource_filepath(name)) as json_file:
            data = json.load(json_file)
    else:
        with open(get_resource_uploadpath(name)) as json_file:
            data = json.load(json_file)
    return data


def pickle_data(data: Any, name: str) -> None:
    with open(get_resource_filepath(name) + '.pickle', 'wb') as pickle_file:
        pickle.dump(data, pickle_file)


def get_pickled_data(name: str) -> Any:
    with open(get_resource_filepath(name) + '.pickle', 'rb') as pickle_file:
        data = pickle.load(pickle_file)
    return data


def export_log_to_csv(log: ObjectCentricLog, name: str) -> None:
    df = export_to_dataframe(log)
    df.to_csv(get_resource_filepath(name), index=False)