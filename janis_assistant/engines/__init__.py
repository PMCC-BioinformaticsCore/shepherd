from typing import Union

from janis_assistant.engines.toil.main import Toil
from .cromwell import Cromwell, CromwellConfiguration
from .enginetypes import EngineType
from .cwltool.main import CWLTool
from .shell.main import Shell
from .engine import Engine
from janis_core import SupportedTranslation


def get_ideal_specification_for_engine(eng: Engine):
    if isinstance(eng, Cromwell):
        return SupportedTranslation.WDL

    elif isinstance(eng, Toil):
        return SupportedTranslation.CWL

    elif isinstance(eng, Shell):
        return SupportedTranslation.SHELL

    return SupportedTranslation.CWL


def get_engine_type(engtype: Union[str, EngineType]):
    engid = str(engtype)
    if engid == EngineType.cromwell.value:
        return Cromwell
    elif engid == EngineType.cwltool.value:
        return CWLTool
    elif engid == EngineType.toil.value:
        return Toil
    elif engid == EngineType.shell.value:
        return Shell

    raise Exception("Couldn't recognise engine type ")
