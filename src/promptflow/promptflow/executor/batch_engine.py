from pathlib import Path
from typing import Any, Dict, List, Mapping, Union

from promptflow._utils.load_data import load_data
from promptflow._utils.multimedia_utils import persist_multimedia_data, resolve_image_path
from promptflow._utils.utils import dump_list_to_jsonl
from promptflow.executor._result import BulkResult
from promptflow.executor.flow_executor import FlowExecutor

OUTPUT_FILE_NAME = "output.jsonl"


class BatchEngine:
    """This class is used to execute flows in batch mode

    :param flow_executor: The executor will be used to run flow in batch mode
    :type flow_executor: ~promptflow.executor.FlowExecutor
    """

    def __init__(self, flow_executor: FlowExecutor):
        """Initialize a BatchEngine object.

        :param flow_executor: The executor will be used to run flow in batch mode
        :type flow_executor: ~promptflow.executor.FlowExecutor
        """
        self.flow_executor = flow_executor

    def run(
        self,
        input_dirs: Dict[str, str],
        inputs_mapping: Dict[str, str],
        output_dir: Path,
        run_id: str = None,
    ) -> BulkResult:
        """Run flow in batch mode

        :param input_dirs: The directories path of input files
        :type input_dirs: Dict[str, str]
        :param inputs_mapping: The mapping of input names to their corresponding values.
        :type inputs_mapping: Dict[str, str]
        :param output_dir: output dir
        :type output_dir: The directory path of output files
        :param run_id: The run id of this run
        :type run_id: str
        :return: The result of this batch run
        :rtype: ~promptflow.executor._result.BulkResult
        """
        input_dicts = self._get_input_dicts(input_dirs, inputs_mapping)
        output_dir = self._resolve_dir(output_dir)
        batch_result = self.flow_executor.exec_bulk(input_dicts, run_id, output_dir=output_dir)
        batch_result.outputs = self._persist_outputs(batch_result.outputs, output_dir)
        return batch_result

    def _get_input_dicts(self, input_dirs: Dict[str, str], inputs_mapping: Dict[str, str]):
        """Resolve input data from input dirs and apply inputs mapping

        TODO: After SDK/CLI can resolve input data from input dirs, this method can be removed.
        """
        input_dicts = self._resolve_data(input_dirs)
        return self.flow_executor.validate_and_apply_inputs_mapping(input_dicts, inputs_mapping)

    def _resolve_data(self, input_dirs: Dict[str, str]):
        """Resolve input data from input dirs"""
        result = {}
        for input_key, input_dir in input_dirs.items():
            input_dir = self._resolve_dir(input_dir)
            file_data = load_data(input_dir)
            for each_line in file_data:
                self._resolve_image(input_dir, each_line)
            result[input_key] = file_data
        return result

    def _resolve_dir(self, dir: Union[str, Path]) -> Path:
        """Resolve input dir to absolute path"""
        path = dir if isinstance(dir, Path) else Path(dir)
        if not path.is_absolute():
            path = self.flow_executor._working_dir / path
        return path

    def _resolve_image(self, input_dir: Path, one_line_data: dict):
        """Resolve image path to absolute path in one line data"""
        for key, value in one_line_data.items():
            if isinstance(value, list):
                for item in value:
                    item = resolve_image_path(input_dir, item)
                one_line_data[key] = value
            elif isinstance(value, dict):
                one_line_data[key] = resolve_image_path(input_dir, value)
        return one_line_data

    def _persist_outputs(self, outputs: List[Mapping[str, Any]], output_dir: Path):
        """Persist outputs to output directory"""
        # persist images to output directory
        outputs = [persist_multimedia_data(output, output_dir) for output in outputs]
        # persist outputs to json line file
        output_file = output_dir / OUTPUT_FILE_NAME
        dump_list_to_jsonl(output_file, outputs)
        return outputs
