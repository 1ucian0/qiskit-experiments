# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Fine drag calibration experiment."""

from typing import List, Optional
import numpy as np

from qiskit.circuit import Gate, QuantumCircuit
from qiskit.providers.backend import Backend
from qiskit.pulse import Play

from qiskit_experiments.exceptions import CalibrationError
from qiskit_experiments.framework import ExperimentData, Options
from qiskit_experiments.calibration_management import (
    BaseCalibrationExperiment,
    BackendCalibrations,
)
from qiskit_experiments.calibration_management.update_library import BaseUpdater
from qiskit_experiments.library.characterization.fine_drag import FineDrag


class FineDragCal(BaseCalibrationExperiment, FineDrag):
    """A calibration version of the fine drag experiment."""

    def __init__(
        self,
        qubit: int,
        calibrations: BackendCalibrations,
        schedule_name: str,
        backend: Optional[Backend] = None,
        cal_parameter_name: Optional[str] = "β",
        auto_update: bool = True,
    ):
        r"""see class :class:`FineDrag` for details.

        Note that this class implicitly assumes that the target angle of the gate
        is :math:`\pi` as seen from the default experiment options.

        Args:
            qubit: The qubit for which to run the fine drag calibration.
            calibrations: The calibrations instance with the schedules.
            schedule_name: The name of the schedule to calibrate.
            backend: Optional, the backend to run the experiment on.
            cal_parameter_name: The name of the parameter in the schedule to update.
            auto_update: Whether or not to automatically update the calibrations. By
                default this variable is set to True.
        """
        super().__init__(
            calibrations,
            qubit,
            Gate(name=schedule_name, num_qubits=1, params=[]),
            schedule_name=schedule_name,
            backend=backend,
            cal_parameter_name=cal_parameter_name,
            auto_update=auto_update,
        )

        self.set_transpile_options(
            inst_map=calibrations.default_inst_map,
            basis_gates=["sx", schedule_name, "rz"],
        )

    @classmethod
    def _default_experiment_options(cls) -> Options:
        """Default experiment options.

        Experiment Options:
            target_angle (float): The target rotation angle of the gate being calibrated.
                This value is needed for the update rule.
        """
        options = super()._default_experiment_options()
        options.target_angle = np.pi
        return options

    def _add_cal_metadata(self, circuits: List[QuantumCircuit]):
        """Add metadata to the circuit to make the experiment data more self contained.

        The following keys are added to each circuit's metadata:
            cal_param_value: The value of the drag parameter. This value together with
                the fit result will be used to find the new value of the drag parameter.
            cal_param_name: The name of the parameter in the calibrations.
            cal_schedule: The name of the schedule in the calibrations.
            target_angle: The target angle of the gate.
            cal_group: The calibration group to which the parameter belongs.
        """

        param_val = self._cals.get_parameter_value(
            self._param_name,
            self.physical_qubits,
            self._sched_name,
            group=self.experiment_options.group,
        )

        for circuit in circuits:
            circuit.metadata["cal_param_value"] = param_val
            circuit.metadata["cal_param_name"] = self._param_name
            circuit.metadata["cal_schedule"] = self._sched_name
            circuit.metadata["target_angle"] = self.experiment_options.target_angle
            circuit.metadata["cal_group"] = self.experiment_options.group

    def update_calibrations(self, experiment_data: ExperimentData):
        """Update the drag parameter of the pulse in the calibrations."""

        data = experiment_data.data()

        # No data -> no update
        if len(data) > 0:

            result_index = self.experiment_options.result_index
            group = data[0]["metadata"]["cal_group"]
            target_angle = data[0]["metadata"]["target_angle"]
            qubits = experiment_data.metadata["physical_qubits"]

            schedule = self._cals.get_schedule(self._sched_name, qubits)

            # Obtain sigma as it is needed for the fine DRAG update rule.
            sigmas = []
            for block in schedule.blocks:
                if isinstance(block, Play) and hasattr(block.pulse, "sigma"):
                    sigmas.append(getattr(block.pulse, "sigma"))

            if len(set(sigmas)) != 1:
                raise CalibrationError(
                    "Cannot run fine Drag calibration on a schedule with multiple values of sigma."
                )

            if len(sigmas) == 0:
                raise CalibrationError(f"Could not infer sigma from {schedule}.")

            d_theta = BaseUpdater.get_value(experiment_data, "d_theta", result_index)

            # See the documentation in fine_drag.py for the derivation of this rule.
            d_beta = -np.sqrt(np.pi) * d_theta * sigmas[0] / target_angle ** 2
            old_beta = data[0]["metadata"]["cal_param_value"]
            new_beta = old_beta + d_beta

            BaseUpdater.add_parameter_value(
                self._cals, experiment_data, new_beta, self._param_name, schedule, group
            )


class FineXDragCal(FineDragCal):
    """Fine drag calibration of X gate."""

    def __init__(
        self,
        qubit: int,
        calibrations: BackendCalibrations,
        backend: Optional[Backend] = None,
        cal_parameter_name: Optional[str] = "β",
        auto_update: bool = True,
    ):
        r"""see class :class:`FineDrag` for details.

        Args:
            qubit: The qubit for which to run the fine drag calibration.
            calibrations: The calibrations instance with the schedules.
            backend: Optional, the backend to run the experiment on.
            cal_parameter_name: The name of the parameter in the schedule to update.
            auto_update: Whether or not to automatically update the calibrations. By
                default this variable is set to True.
        """
        super().__init__(
            qubit,
            calibrations,
            schedule_name="x",
            backend=backend,
            cal_parameter_name=cal_parameter_name,
            auto_update=auto_update,
        )


class FineSXDragCal(FineDragCal):
    """Fine drag calibration of X gate."""

    def __init__(
        self,
        qubit: int,
        calibrations: BackendCalibrations,
        backend: Optional[Backend] = None,
        cal_parameter_name: Optional[str] = "β",
        auto_update: bool = True,
    ):
        r"""see class :class:`FineDrag` for details.

        Args:
            qubit: The qubit for which to run the fine drag calibration.
            calibrations: The calibrations instance with the schedules.
            backend: Optional, the backend to run the experiment on.
            cal_parameter_name: The name of the parameter in the schedule to update.
            auto_update: Whether or not to automatically update the calibrations. By
                default this variable is set to True.
        """
        super().__init__(
            qubit,
            calibrations,
            schedule_name="sx",
            backend=backend,
            cal_parameter_name=cal_parameter_name,
            auto_update=auto_update,
        )

    @classmethod
    def _default_experiment_options(cls) -> Options:
        """Default experiment options."""
        options = super()._default_experiment_options()
        options.target_angle = np.pi / 2
        return options
