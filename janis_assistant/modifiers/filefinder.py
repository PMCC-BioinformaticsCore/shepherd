import os.path
from typing import Dict, List, Union, Optional

from janis_assistant.management.filescheme import FileScheme
from janis_core import (
    Tool,
    WorkflowBase,
    Logger,
    File,
    Array,
    DataType,
    apply_secondary_file_format_to_filename,
    InputDocumentation,
)

from janis_assistant.modifiers.base import PipelineModifierBase


class FileFinderModifier(PipelineModifierBase):
    def __init__(self, cache_dir: str, source_hints: List[str] = None):
        self.cache_dir = cache_dir
        self.source_hints: List[str] = source_hints or []

    def inputs_modifier(self, tool: Tool, inputs: Dict, hints: Dict[str, str]) -> Dict:

        if not isinstance(tool, WorkflowBase):
            return inputs

        wf: WorkflowBase = tool
        new_inputs = {}

        for inpnode in wf.input_nodes.values():
            if inpnode.id() in inputs and inputs[inpnode.id()] is not None:
                continue
            elif inpnode.default is not None or inpnode.datatype.optional:
                continue
            elif not (
                isinstance(inpnode.datatype, File)
                or (
                    isinstance(inpnode.datatype, Array)
                    and isinstance(inpnode.datatype.fundamental_type(), File)
                )
            ):
                # If it's not a File or Array[File], then continue (we can't localise it anyway)
                continue
            elif inpnode.doc is None or inpnode.doc.source is None:
                continue

            Logger.info(
                f"An input to '{wf.id()}.{inpnode.id()}' was not found, and the workflow specifies a source to potentially locate from."
            )

            doc: InputDocumentation = inpnode.doc

            # use the source hints to find
            source = self.determine_appropriate_source_from_hints(
                tool, inpnode.id(), doc.source
            )
            if source:
                basedir = os.path.join(self.cache_dir, inpnode.id())
                os.makedirs(basedir, exist_ok=True)

                new_inputs[inpnode.id()] = self.localise_inputs(
                    inpnode.id(),
                    inpnode.datatype,
                    basedir,
                    source,
                    localise_secondary_files=not doc.skip_sourcing_secondary_files,
                )

        return {**inputs, **new_inputs}

    def localise_inputs(
        self,
        inpid: str,
        inptype: DataType,
        dest_dir: str,
        source: Union[str, List[str]],
        localise_secondary_files: bool = True,
    ):
        if isinstance(source, list):
            return [self.localise_inputs(inpid, inptype, dest_dir, s) for s in source]

        fs = FileScheme.get_type_by_prefix(source)()

        out_path = os.path.join(dest_dir, os.path.basename(source))
        if os.path.exists(out_path):
            Logger.info(
                f"A file already exists when localising '{inpid}' at '{out_path}'. If this isn't the right file, "
                f"you'll need to manually remove this file before proceeding"
            )
        else:
            try:
                fs.cp_from(source, out_path)
            except Exception as e:
                Logger.critical(
                    f"Couldn't localise source from {source} -> {out_path}: {repr(e)}"
                )
                raise

        if localise_secondary_files:
            try:
                for sec in inptype.secondary_files() or []:
                    sec_source = apply_secondary_file_format_to_filename(source, sec)
                    out_sec_path = apply_secondary_file_format_to_filename(
                        out_path, sec
                    )

                    if os.path.exists(out_sec_path):
                        Logger.info(
                            f"The secondary file for {inpid} ({sec}) already exists when localising '{inpid}' at '{out_sec_path}'. If this isn't the right file, "
                            f"you'll need to manually remove this file before proceeding"
                        )
                    elif not fs.exists(sec_source):
                        Logger.warn(
                            f"Couldn't find the secondary file for {inpid}, expected at {sec_source}, skipping for now"
                        )
                    else:
                        fs.cp_from(sec_source, out_sec_path)

            except Exception as e:
                Logger.critical(f"Couldn't localise secondary file due to: {e}")

        return out_path

    def determine_appropriate_source_from_hints(
        self,
        tool: Tool,
        inpid: str,
        source: Union[str, List[str], Dict[str, Union[str, List[str]]]],
    ) -> Optional[Union[str, List[str]]]:

        if isinstance(source, str) or isinstance(source, list):
            return source

        elif not isinstance(source, dict):
            Logger.critical(
                f"The input to the tool '{tool.id()}'.'{inpid}' did not have the correct format for doc.source, "
                f"expected Union[str, List[str], Dict[str, Union[str, List[str]]]], received '{type(source)}'"
            )

        tishj = ", ".join(source.keys())
        if not self.source_hints or len(self.source_hints) == 0:
            Logger.warn(
                f"There were no source hints specified to find an input for {tool.id()}.{inpid}, expected one "
                f"or more of {tishj}. You can specify source hints with --source-hint (in janis prepare)."
            )
            return None

        for hint in self.source_hints:
            if hint in source:
                return source[hint]

        shj = ", ".join(self.source_hints)
        Logger.warn(
            f"Couldn't find any of the specified source_hints ({shj}) in the tool input {tool.id()}.{inpid}'s source fields ({tishj})"
        )
        return None