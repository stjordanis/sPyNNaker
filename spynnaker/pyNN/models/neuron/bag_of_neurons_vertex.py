
# pacman imports
from pacman.model.abstract_classes.abstract_has_global_max_atoms import \
    AbstractHasGlobalMaxAtoms
from pacman.model.constraints.key_allocator_constraints\
    .key_allocator_contiguous_range_constraint \
    import KeyAllocatorContiguousRangeContraint
from pacman.model.decorators.overrides import overrides
from pacman.executor.injection_decorator import inject_items
from pacman.model.graphs.application.impl.application_vertex \
    import ApplicationVertex
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.sdram_resource import SDRAMResource

# front end common imports
from spinn_front_end_common.abstract_models\
    .abstract_binary_uses_simulation_run import AbstractBinaryUsesSimulationRun
from spinn_front_end_common.abstract_models.\
    abstract_provides_incoming_partition_constraints import \
    AbstractProvidesIncomingPartitionConstraints
from spinn_front_end_common.abstract_models.\
    abstract_provides_outgoing_partition_constraints import \
    AbstractProvidesOutgoingPartitionConstraints
from spinn_front_end_common.utilities import constants as \
    common_constants
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.abstract_models\
    .abstract_generates_data_specification \
    import AbstractGeneratesDataSpecification
from spinn_front_end_common.abstract_models.abstract_has_associated_binary \
    import AbstractHasAssociatedBinary

from spinn_front_end_common.interface.buffer_management\
    .buffer_models.receives_buffers_to_host_basic_impl \
    import ReceiveBuffersToHostBasicImpl

# spynnaker imports
from spynnaker.pyNN.models.abstract_models.abstract_groupable import \
    AbstractGroupable
from spynnaker.pyNN.models.neuron.synaptic_manager import SynapticManager
from spynnaker.pyNN.utilities import utility_calls
from spynnaker.pyNN.models.common import recording_utils
from spynnaker.pyNN.models.abstract_models.abstract_population_initializable \
    import AbstractPopulationInitializable
from spynnaker.pyNN.models.abstract_models.abstract_population_settable \
    import AbstractPopulationSettable
from spinn_front_end_common.abstract_models.abstract_changable_after_run \
    import AbstractChangableAfterRun
from spynnaker.pyNN.models.common.abstract_spike_recordable \
    import AbstractSpikeRecordable
from spynnaker.pyNN.models.common.abstract_v_recordable \
    import AbstractVRecordable
from spynnaker.pyNN.models.common.abstract_gsyn_recordable \
    import AbstractGSynRecordable
from spynnaker.pyNN.models.common.spike_recorder import SpikeRecorder
from spynnaker.pyNN.models.common.v_recorder import VRecorder
from spynnaker.pyNN.models.common.gsyn_recorder import GsynRecorder
from spynnaker.pyNN.utilities import constants
from spynnaker.pyNN.utilities.conf import config
from spynnaker.pyNN.models.neuron.bag_of_neurons_machine_vertex \
    import BagOfNeuronsMachineVertex
from spynnaker.pyNN.models.neuron_cell import RecordingType

import logging
import os

logger = logging.getLogger(__name__)

# TODO: Make sure these values are correct (particularly CPU cycles)
_NEURON_BASE_DTCM_USAGE_IN_BYTES = 36
_NEURON_BASE_SDRAM_USAGE_IN_BYTES = 12
_NEURON_BASE_N_CPU_CYCLES_PER_NEURON = 22
_NEURON_BASE_N_CPU_CYCLES = 10

# TODO: Make sure these values are correct (particularly CPU cycles)
_C_MAIN_BASE_DTCM_USAGE_IN_BYTES = 12
_C_MAIN_BASE_SDRAM_USAGE_IN_BYTES = 72
_C_MAIN_BASE_N_CPU_CYCLES = 0


class BagOfNeuronsVertex(
        ApplicationVertex, AbstractGeneratesDataSpecification,
        AbstractHasAssociatedBinary, AbstractBinaryUsesSimulationRun,
        AbstractSpikeRecordable, AbstractVRecordable, AbstractGSynRecordable,
        AbstractProvidesOutgoingPartitionConstraints,
        AbstractProvidesIncomingPartitionConstraints,
        AbstractChangableAfterRun, AbstractGroupable,
        AbstractHasGlobalMaxAtoms):
    """ Underlying vertex model for Neural Populations.
    """

    is_array_parameters = {}
    fixed_parameters = {}
    population_parameters = {
        'spikes_per_second', 'ring_buffer_sigma',
        '', 'machine_time_step',
        'time_scale_factor', 'model_class', 'label', 'constraints'}

    @staticmethod
    def default_parameters(class_object):
        parameters = dict()
        parameters.update(class_object.neuron_model.default_parameters())
        parameters.update(class_object.synapse_type.default_parameters())
        parameters.update(class_object.input_type.default_parameters())
        parameters.update(class_object.threshold_type.default_parameters())
        if hasattr(class_object, "additional_input"):
            parameters.update(
                class_object.additional_input.default_parameters())
        return parameters

    @staticmethod
    def fixed_parameters(class_object):
        parameters = dict()
        parameters.update(class_object.neuron_model.fixed_parameters())
        parameters.update(class_object.synapse_type.fixed_parameters())
        parameters.update(class_object.input_type.fixed_parameters())
        parameters.update(class_object.threshold_type.fixed_parameters())
        if hasattr(class_object, "additional_input"):
            parameters.update(
                class_object.additional_input.fixed_parameters())
        return parameters

    @staticmethod
    def state_variables(class_object):
        parameters = list()
        parameters.extend(class_object.neuron_model.state_variables())
        parameters.extend(class_object.synapse_type.state_variables())
        parameters.extend(class_object.input_type.state_variables())
        parameters.extend(class_object.threshold_type.state_variables())
        if hasattr(class_object, "additional_input"):
            parameters.extend(
                class_object.additional_input.state_variables())
        return parameters

    @staticmethod
    def is_array_parameters(class_object):
        parameters = dict()
        parameters.update(class_object.neuron_model.is_array_parameters())
        parameters.update(class_object.synapse_type.is_array_parameters())
        parameters.update(class_object.input_type.is_array_parameters())
        parameters.update(class_object.threshold_type.is_array_parameters())
        if hasattr(class_object, "additional_input"):
            parameters.update(
                class_object.additional_input.is_array_parameters())
        return parameters

    @staticmethod
    def recording_types(_):
        return [RecordingType.SPIKES, RecordingType.V, RecordingType.GSYN]

    def __init__(
            self, bag_of_neurons, label, model_class,
            spikes_per_second=None, ring_buffer_sigma=None,
            incoming_spike_buffer_size=None, constraints=None):

        ApplicationVertex.__init__(
            self, label, constraints,
            model_class.model_based_max_atoms_per_core)
        AbstractSpikeRecordable.__init__(self)
        AbstractVRecordable.__init__(self)
        AbstractGSynRecordable.__init__(self)
        AbstractProvidesOutgoingPartitionConstraints.__init__(self)
        AbstractProvidesIncomingPartitionConstraints.__init__(self)
        AbstractPopulationInitializable.__init__(self)
        AbstractPopulationSettable.__init__(self)
        AbstractChangableAfterRun.__init__(self)
        AbstractGroupable.__init__(self)

        self._binary = model_class.binary_name
        self._label = label
        self._incoming_spike_buffer_size = incoming_spike_buffer_size
        if incoming_spike_buffer_size is None:
            self._incoming_spike_buffer_size = config.getint(
                "Simulation", "incoming_spike_buffer_size")

        self._model_name = model_class.model_name
        self._neuron_model = model_class.neuron_model(bag_of_neurons)
        self._input_type = model_class.input_type(bag_of_neurons)
        self._threshold_type = model_class.threshold_type(bag_of_neurons)
        synapse_type = model_class.synapse_type(bag_of_neurons)

        self._additional_input = None
        if hasattr(model_class, "additional_input"):
            self._additional_input = \
                model_class.additional_input(bag_of_neurons)

        # storage of atoms for usage during sets and records
        self._atoms = bag_of_neurons
        self._vertex_to_pop_mapping = None

        # Set up for recording
        self._spike_recorder = SpikeRecorder()
        self._v_recorder = VRecorder()
        self._gsyn_recorder = GsynRecorder()

        # check the bag of neurons for recording states
        for atom in bag_of_neurons:
            if atom.is_recording(RecordingType.SPIKES):
                self._change_requires_mapping = not self._spike_recorder.record
                self._spike_recorder.record = True
            if atom.is_recording(RecordingType.V):
                self._change_requires_mapping = not self._v_recorder.record_v
                self._v_recorder.record_v = True
            if atom.is_recording(RecordingType.GSYN):
                self._change_requires_mapping = \
                    not self._gsyn_recorder.record_gsyn
                self._gsyn_recorder.record_gsyn = True

        self._spike_buffer_max_size = config.getint(
            "Buffers", "spike_buffer_size")
        self._v_buffer_max_size = config.getint(
            "Buffers", "v_buffer_size")
        self._gsyn_buffer_max_size = config.getint(
            "Buffers", "gsyn_buffer_size")
        self._buffer_size_before_receive = config.getint(
            "Buffers", "buffer_size_before_receive")
        self._time_between_requests = config.getint(
            "Buffers", "time_between_requests")
        self._minimum_buffer_sdram = config.getint(
            "Buffers", "minimum_buffer_sdram")
        self._using_auto_pause_and_resume = config.getboolean(
            "Buffers", "use_auto_pause_and_resume")
        self._receive_buffer_host = config.get(
            "Buffers", "receive_buffer_host")
        self._receive_buffer_port = config.getint(
            "Buffers", "receive_buffer_port")
        self._enable_buffered_recording = config.getboolean(
            "Buffers", "enable_buffered_recording")

        # Set up synapse handling
        self._synapse_manager = SynapticManager(
            synapse_type, ring_buffer_sigma,
            spikes_per_second)

        # bool for if state has changed.
        self._change_requires_mapping = True

    @property
    @overrides(ApplicationVertex.n_atoms)
    def n_atoms(self):
        return self._n_atoms

    @inject_items({
        "graph": "MemoryApplicationGraph",
        "n_machine_time_steps": "TotalMachineTimeSteps",
        "machine_time_step": "MachineTimeStep"
    })
    @overrides(
        ApplicationVertex.get_resources_used_by_atoms,
        additional_arguments={
            "graph", "n_machine_time_steps", "machine_time_step"
        }
    )
    def get_resources_used_by_atoms(
            self, vertex_slice, graph, n_machine_time_steps,
            machine_time_step):

        # set resources required from this object
        container = ResourceContainer(
            sdram=SDRAMResource(
                self.get_sdram_usage_for_atoms(
                    vertex_slice, graph, n_machine_time_steps,
                    machine_time_step)),
            dtcm=DTCMResource(self.get_dtcm_usage_for_atoms(vertex_slice)),
            cpu_cycles=CPUCyclesPerTickResource(
                self.get_cpu_usage_for_atoms(vertex_slice)))

        # set up any resources config needed for the auto pause and resume
        self._check_for_auto_pause_and_resume_functionality(
            vertex_slice, self, n_machine_time_steps)

        # add extra resources from the extra functionality
        container.extend(self.get_extra_resources(
            self._receive_buffer_host, self._receive_buffer_port))

        # return the total resources.
        return container

    def set_mapping(self, vertex_mapping):
        self._synapse_manager.set_mapping(vertex_mapping)

    @property
    def vertex_to_pop_mapping(self):
        return self._synapse_manager.vertex_to_pop_mapping

    @property
    @overrides(AbstractChangableAfterRun.requires_mapping)
    def requires_mapping(self):
        return self._change_requires_mapping

    @overrides(AbstractChangableAfterRun.mark_no_changes)
    def mark_no_changes(self):
        self._change_requires_mapping = False

    def requires_remapping_for_change(self, parameter, old_value, new_value):
        return True

    @staticmethod
    def create_vertex(bag_of_neurons, population_parameters):
        """

        :param bag_of_neurons:
        :param population_parameters:
        :return:
        """
        params = dict(population_parameters)
        params['bag_of_neurons'] = bag_of_neurons
        vertex = BagOfNeuronsVertex(**params)
        return vertex

    def _check_for_auto_pause_and_resume_functionality(
            self, vertex_slice, object_to_set, n_machine_time_steps):
        if not self._using_auto_pause_and_resume:
            spike_buffer_size = self._spike_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, n_machine_time_steps)
            v_buffer_size = self._v_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, n_machine_time_steps)
            gsyn_buffer_size = self._gsyn_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, n_machine_time_steps)
            spike_buffering_needed = recording_utils.needs_buffering(
                self._spike_buffer_max_size, spike_buffer_size,
                self._enable_buffered_recording)
            v_buffering_needed = recording_utils.needs_buffering(
                self._v_buffer_max_size, v_buffer_size,
                self._enable_buffered_recording)
            gsyn_buffering_needed = recording_utils.needs_buffering(
                self._gsyn_buffer_max_size, gsyn_buffer_size,
                self._enable_buffered_recording)
            if (spike_buffering_needed or v_buffering_needed or
                    gsyn_buffering_needed):
                object_to_set.activate_buffering_output(
                    buffering_ip_address=self._receive_buffer_host,
                    buffering_port=self._receive_buffer_port)
        else:
            sdram_per_ts = 0
            sdram_per_ts += self._spike_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, 1)
            sdram_per_ts += self._v_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, 1)
            sdram_per_ts += self._gsyn_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, 1)
            object_to_set.activate_buffering_output(
                minimum_sdram_for_buffering=self._minimum_buffer_sdram,
                buffered_sdram_per_timestep=sdram_per_ts)

    @inject_items({"n_machine_time_steps": "TotalMachineTimeSteps"})
    @overrides(
        ApplicationVertex.create_machine_vertex,
        additional_arguments={"n_machine_time_steps"})
    def create_machine_vertex(
            self, vertex_slice, resources_required, n_machine_time_steps,
            label=None, constraints=None):

        is_recording = (
            self._gsyn_recorder.record_gsyn or self._v_recorder.record_v or
            self._spike_recorder.record
        )

        # handle any new resources from the interfaces
        resources_required.extend(self.get_extra_resources(
            self._receive_buffer_host, self._receive_buffer_port))

        vertex = BagOfNeuronsMachineVertex(
            resources_required, is_recording, label, constraints)

        # check for auto pause and resume setting
        self._check_for_auto_pause_and_resume_functionality(
            vertex_slice, vertex, n_machine_time_steps)

        # return machine vertex
        return vertex

    def get_maximum_delay_supported_in_ms(self, machine_time_step):
        return self._synapse_manager.get_maximum_delay_supported_in_ms(
            machine_time_step)

    def get_cpu_usage_for_atoms(self, vertex_slice):
        per_neuron_cycles = (
            _NEURON_BASE_N_CPU_CYCLES_PER_NEURON +
            self._neuron_model.get_n_cpu_cycles_per_neuron() +
            self._input_type.get_n_cpu_cycles_per_neuron(
                self._synapse_manager.synapse_type.get_n_synapse_types()) +
            self._threshold_type.get_n_cpu_cycles_per_neuron())
        if self._additional_input is not None:
            per_neuron_cycles += \
                self._additional_input.get_n_cpu_cycles_per_neuron()
        return (_NEURON_BASE_N_CPU_CYCLES +
                _C_MAIN_BASE_N_CPU_CYCLES +
                (per_neuron_cycles * vertex_slice.n_atoms) +
                self._spike_recorder.get_n_cpu_cycles(vertex_slice.n_atoms) +
                self._v_recorder.get_n_cpu_cycles(vertex_slice.n_atoms) +
                self._gsyn_recorder.get_n_cpu_cycles(vertex_slice.n_atoms) +
                self._synapse_manager.get_n_cpu_cycles())

    def get_dtcm_usage_for_atoms(self, vertex_slice):
        per_neuron_usage = (
            self._neuron_model.get_dtcm_usage_per_neuron_in_bytes() +
            self._input_type.get_dtcm_usage_per_neuron_in_bytes() +
            self._threshold_type.get_dtcm_usage_per_neuron_in_bytes())
        if self._additional_input is not None:
            per_neuron_usage += \
                self._additional_input.get_dtcm_usage_per_neuron_in_bytes()
        return (_NEURON_BASE_DTCM_USAGE_IN_BYTES +
                (per_neuron_usage * vertex_slice.n_atoms) +
                self._spike_recorder.get_dtcm_usage_in_bytes() +
                self._v_recorder.get_dtcm_usage_in_bytes() +
                self._gsyn_recorder.get_dtcm_usage_in_bytes() +
                self._synapse_manager.get_dtcm_usage_in_bytes())

    def _get_sdram_usage_for_neuron_params(self, vertex_slice):
        per_neuron_usage = (
            self._input_type.get_sdram_usage_per_neuron_in_bytes() +
            self._threshold_type.get_sdram_usage_per_neuron_in_bytes())
        if self._additional_input is not None:
            per_neuron_usage += \
                self._additional_input.get_sdram_usage_per_neuron_in_bytes()
        return (common_constants.SYSTEM_BYTES_REQUIREMENT +
                ReceiveBuffersToHostBasicImpl.get_recording_data_size(3) +
                (per_neuron_usage * vertex_slice.n_atoms) +
                self._neuron_model.get_sdram_usage_in_bytes(
                    vertex_slice.n_atoms))

    def get_sdram_usage_for_atoms(
            self, vertex_slice, graph, n_machine_time_steps,
            machine_time_step):
        sdram_requirement = (
            self._get_sdram_usage_for_neuron_params(vertex_slice) +
            ReceiveBuffersToHostBasicImpl.get_buffer_state_region_size(3) +
            BagOfNeuronsMachineVertex.get_provenance_data_size(
                BagOfNeuronsMachineVertex.N_ADDITIONAL_PROVENANCE_DATA_ITEMS) +
            self._synapse_manager.get_sdram_usage_in_bytes(
                vertex_slice, graph.get_edges_ending_at_vertex(self),
                machine_time_step) +
            (self._get_number_of_mallocs_used_by_dsg() *
             common_constants.SARK_PER_MALLOC_SDRAM_USAGE))

        # add recording SDRAM if not automatically calculated
        if not self._using_auto_pause_and_resume:
            spike_buffer_size = self._spike_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, n_machine_time_steps)
            v_buffer_size = self._v_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, n_machine_time_steps)
            gsyn_buffer_size = self._gsyn_recorder.get_sdram_usage_in_bytes(
                vertex_slice.n_atoms, n_machine_time_steps)
            sdram_requirement += recording_utils.get_buffer_sizes(
                self._spike_buffer_max_size, spike_buffer_size,
                self._enable_buffered_recording)
            sdram_requirement += recording_utils.get_buffer_sizes(
                self._v_buffer_max_size, v_buffer_size,
                self._enable_buffered_recording)
            sdram_requirement += recording_utils.get_buffer_sizes(
                self._gsyn_buffer_max_size, gsyn_buffer_size,
                self._enable_buffered_recording)
        else:
            sdram_requirement += self._minimum_buffer_sdram

        return sdram_requirement

    def _get_number_of_mallocs_used_by_dsg(self):
        extra_mallocs = 0
        if self._gsyn_recorder.record_gsyn:
            extra_mallocs += 1
        if self._v_recorder.record_v:
            extra_mallocs += 1
        if self._spike_recorder.record:
            extra_mallocs += 1
        return (
            self.BASIC_MALLOC_USAGE +
            self._synapse_manager.get_number_of_mallocs_used_by_dsg() +
            extra_mallocs)

    def _reserve_memory_regions(
            self, spec, vertex_slice, spike_history_region_sz,
            v_history_region_sz, gsyn_history_region_sz, vertex):

        spec.comment("\nReserving memory space for data regions:\n\n")

        # Reserve memory:
        spec.reserve_memory_region(
            region=constants.POPULATION_BASED_REGIONS.SYSTEM.value,
            size=(
                common_constants.SYSTEM_BYTES_REQUIREMENT +
                vertex.get_recording_data_size(3)), label='System')

        spec.reserve_memory_region(
            region=constants.POPULATION_BASED_REGIONS.NEURON_PARAMS.value,
            size=self._get_sdram_usage_for_neuron_params(vertex_slice),
            label='NeuronParams')

        vertex.reserve_buffer_regions(
            spec,
            constants.POPULATION_BASED_REGIONS.BUFFERING_OUT_STATE.value,
            [constants.POPULATION_BASED_REGIONS.SPIKE_HISTORY.value,
             constants.POPULATION_BASED_REGIONS.POTENTIAL_HISTORY.value,
             constants.POPULATION_BASED_REGIONS.GSYN_HISTORY.value],
            [spike_history_region_sz, v_history_region_sz,
             gsyn_history_region_sz])

        vertex.reserve_provenance_data_region(spec)

    def _write_setup_info(
            self, spec, spike_history_region_sz, neuron_potential_region_sz,
            gsyn_region_sz, ip_tags, buffer_size_before_receive,
            time_between_requests, vertex, machine_time_step,
            time_scale_factor):
        """ Write information used to control the simulation and gathering of\
            results.
        """

        # Write the data needed by the simulation interface
        spec.switch_write_focus(
            constants.POPULATION_BASED_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # Write the data needed for the buffered regions
        vertex.write_recording_data(
            spec, ip_tags,
            [spike_history_region_sz, neuron_potential_region_sz,
             gsyn_region_sz], buffer_size_before_receive,
            time_between_requests)

    def _write_neuron_parameters(
            self, spec, key, vertex_slice):

        n_atoms = (vertex_slice.hi_atom - vertex_slice.lo_atom) + 1
        spec.comment("\nWriting Neuron Parameters for {} Neurons:\n".format(
            n_atoms))

        # Set the focus to the memory region 2 (neuron parameters):
        spec.switch_write_focus(
            region=constants.POPULATION_BASED_REGIONS.NEURON_PARAMS.value)

        # Write whether the key is to be used, and then the key, or 0 if it
        # isn't to be used
        if key is None:
            spec.write_value(data=0)
            spec.write_value(data=0)
        else:
            spec.write_value(data=1)
            spec.write_value(data=key)

        # Write the number of neurons in the block:
        spec.write_value(data=n_atoms)

        # Write the size of the incoming spike buffer
        spec.write_value(data=self._incoming_spike_buffer_size)

        # Write the global parameters
        global_params = self._neuron_model.get_global_parameters()
        for param in global_params:
            spec.write_value(data=param.get_value(),
                             data_type=param.get_dataspec_datatype())

        # Write the neuron parameters
        utility_calls.write_parameters_per_neuron(
            spec, vertex_slice, self._neuron_model.get_neural_parameters)

        # Write the input type parameters
        utility_calls.write_parameters_per_neuron(
            spec, vertex_slice, self._input_type.get_input_type_parameters)

        # Write the additional input parameters
        if self._additional_input is not None:
            utility_calls.write_parameters_per_neuron(
                spec, vertex_slice, self._additional_input.get_parameters)

        # Write the threshold type parameters
        utility_calls.write_parameters_per_neuron(
            spec, vertex_slice,
            self._threshold_type.get_threshold_parameters)

    @inject_items({
        "machine_time_step": "MachineTimeStep",
        "time_scale_factor": "TimeScaleFactor",
        "graph_mapper": "MemoryGraphMapper",
        "application_graph": "MemoryApplicationGraph",
        "machine_graph": "MemoryMachineGraph",
        "routing_info": "MemoryRoutingInfos",
        "tags": "MemoryTags",
        "n_machine_time_steps": "TotalMachineTimeSteps"
    })
    @overrides(
        AbstractGeneratesDataSpecification.generate_data_specification,
        additional_arguments={
            "machine_time_step", "time_scale_factor", "graph_mapper",
            "application_graph", "machine_graph", "routing_info", "tags",
            "n_machine_time_steps"
        })
    def generate_data_specification(
            self, spec, placement, machine_time_step, time_scale_factor,
            graph_mapper, application_graph, machine_graph, routing_info,
            tags, n_machine_time_steps):
        vertex = placement.vertex

        spec.comment("\n*** Spec for block of {} neurons ***\n".format(
            self._model_name))
        vertex_slice = graph_mapper.get_slice(vertex)

        # Get recording sizes - the order is important here as spikes will
        # require less space than voltage and voltage less than gsyn.  This
        # order ensures that the buffer size before receive is optimum for
        # all recording channels
        # TODO: Maybe split the buffer size before receive by channel?
        spike_buffer_size = self._spike_recorder.get_sdram_usage_in_bytes(
            vertex_slice.n_atoms, n_machine_time_steps)
        v_buffer_size = self._v_recorder.get_sdram_usage_in_bytes(
            vertex_slice.n_atoms, n_machine_time_steps)
        gsyn_buffer_size = self._gsyn_recorder.get_sdram_usage_in_bytes(
            vertex_slice.n_atoms, n_machine_time_steps)
        spike_history_sz = recording_utils.get_buffer_sizes(
            self._spike_buffer_max_size, spike_buffer_size,
            self._enable_buffered_recording)
        v_history_sz = recording_utils.get_buffer_sizes(
            self._v_buffer_max_size, v_buffer_size,
            self._enable_buffered_recording)
        gsyn_history_sz = recording_utils.get_buffer_sizes(
            self._gsyn_buffer_max_size, gsyn_buffer_size,
            self._enable_buffered_recording)
        spike_buffering_needed = recording_utils.needs_buffering(
            self._spike_buffer_max_size, spike_buffer_size,
            self._enable_buffered_recording)
        v_buffering_needed = recording_utils.needs_buffering(
            self._v_buffer_max_size, v_buffer_size,
            self._enable_buffered_recording)
        gsyn_buffering_needed = recording_utils.needs_buffering(
            self._gsyn_buffer_max_size, gsyn_buffer_size,
            self._enable_buffered_recording)
        buffer_size_before_receive = self._buffer_size_before_receive
        if (not spike_buffering_needed and not v_buffering_needed and
                not gsyn_buffering_needed):
            buffer_size_before_receive = max((
                spike_history_sz, v_history_sz, gsyn_history_sz)) + 256

        # Reserve memory regions
        self._reserve_memory_regions(
            spec, vertex_slice, spike_history_sz, v_history_sz,
            gsyn_history_sz, vertex)

        # Declare random number generators and distributions:
        # TODO add random distribution stuff
        # self.write_random_distribution_declarations(spec)

        # Get the key
        key = routing_info.get_first_key_from_pre_vertex(
            vertex, constants.SPIKE_PARTITION_ID)

        # Write the regions
        iptags = tags.get_ip_tags_for_vertex(vertex)
        self._write_setup_info(
            spec, spike_history_sz, v_history_sz, gsyn_history_sz,
            iptags, buffer_size_before_receive, self._time_between_requests,
            vertex, machine_time_step, time_scale_factor)
        self._write_neuron_parameters(spec, key, vertex_slice)

        # allow the synaptic matrix to write its data spec-able data
        self._synapse_manager.write_data_spec(
            spec, self, vertex_slice, vertex, placement, machine_graph,
            application_graph, routing_info, graph_mapper,
            self._input_type, machine_time_step)

        # End the writing of this specification:
        spec.end_specification()

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):

        # Split binary name into title and extension
        binary_title, binary_extension = os.path.splitext(self._binary)

        # Reunite title and extension and return
        return (binary_title + self._synapse_manager.vertex_executable_suffix +
                binary_extension)

    @overrides(AbstractSpikeRecordable.is_recording_spikes)
    def is_recording_spikes(self):
        return self._spike_recorder.record

    @overrides(AbstractSpikeRecordable.set_recording_spikes)
    def set_recording_spikes(self):
        self._change_requires_mapping = not self._spike_recorder.record
        self._spike_recorder.record = True

    @overrides(AbstractSpikeRecordable.get_spikes)
    def get_spikes(
            self, placements, graph_mapper, buffer_manager, machine_time_step):
        return self._spike_recorder.get_spikes(
            self._label, buffer_manager,
            constants.POPULATION_BASED_REGIONS.SPIKE_HISTORY.value,
            constants.POPULATION_BASED_REGIONS.BUFFERING_OUT_STATE.value,
            placements, graph_mapper, self, machine_time_step)

    @overrides(AbstractVRecordable.is_recording_v)
    def is_recording_v(self):
        return self._v_recorder.record_v

    @overrides(AbstractVRecordable.set_recording_v)
    def set_recording_v(self):
        self._change_requires_mapping = not self._v_recorder.record_v
        self._v_recorder.record_v = True

    @overrides(AbstractVRecordable.get_v)
    def get_v(self, n_machine_time_steps, placements, graph_mapper,
              buffer_manager, machine_time_step):
        return self._v_recorder.get_v(
            self._label, buffer_manager,
            constants.POPULATION_BASED_REGIONS.POTENTIAL_HISTORY.value,
            constants.POPULATION_BASED_REGIONS.BUFFERING_OUT_STATE.value,
            placements, graph_mapper, self, machine_time_step)

    @overrides(AbstractGSynRecordable.is_recording_gsyn)
    def is_recording_gsyn(self):
        return self._gsyn_recorder.record_gsyn

    @overrides(AbstractGSynRecordable.set_recording_gsyn)
    def set_recording_gsyn(self):
        self._change_requires_mapping = not self._gsyn_recorder.record_gsyn
        self._gsyn_recorder.record_gsyn = True

    @overrides(AbstractGSynRecordable.get_gsyn)
    def get_gsyn(
            self, n_machine_time_steps, placements, graph_mapper,
            buffer_manager, machine_time_step):
        return self._gsyn_recorder.get_gsyn(
            self._label, buffer_manager,
            constants.POPULATION_BASED_REGIONS.GSYN_HISTORY.value,
            constants.POPULATION_BASED_REGIONS.BUFFERING_OUT_STATE.value,
            placements, graph_mapper, self, machine_time_step)

    @property
    def synapse_type(self):
        return self._synapse_manager.synapse_type

    @property
    def input_type(self):
        return self._input_type

    @property
    def weight_scale(self):
        return self._input_type.get_global_weight_scale()

    @property
    def ring_buffer_sigma(self):
        return self._synapse_manager.ring_buffer_sigma

    @ring_buffer_sigma.setter
    def ring_buffer_sigma(self, ring_buffer_sigma):
        self._synapse_manager.ring_buffer_sigma = ring_buffer_sigma

    @property
    def spikes_per_second(self):
        return self._synapse_manager.spikes_per_second

    @spikes_per_second.setter
    def spikes_per_second(self, spikes_per_second):
        self._synapse_manager.spikes_per_second = spikes_per_second

    @property
    def synapse_dynamics(self):
        return self._synapse_manager.synapse_dynamics

    @synapse_dynamics.setter
    def synapse_dynamics(self, synapse_dynamics):
        self._synapse_manager.synapse_dynamics = synapse_dynamics

    def add_pre_run_connection_holder(
            self, connection_holder, edge, synapse_info):
        self._synapse_manager.add_pre_run_connection_holder(
            connection_holder, edge, synapse_info)

    def get_connections_from_machine(
            self, transceiver, placement, edge, graph_mapper,
            routing_infos, synapse_info, machine_time_step):
        return self._synapse_manager.get_connections_from_machine(
            transceiver, placement, edge, graph_mapper,
            routing_infos, synapse_info, machine_time_step)

    @overrides(AbstractProvidesIncomingPartitionConstraints.
               get_incoming_partition_constraints)
    def get_incoming_partition_constraints(self, partition):
        """ Gets the constraints for partitions going into this vertex

        :param partition: partition that goes into this vertex
        :return: list of constraints
        """
        return self._synapse_manager.get_incoming_partition_constraints()

    @overrides(AbstractProvidesOutgoingPartitionConstraints.
               get_outgoing_partition_constraints)
    def get_outgoing_partition_constraints(self, partition):
        """ Gets the constraints for partitions going out of this vertex
        :param partition: the partition that leaves this vertex
        :return: list of constraints
        """
        return [KeyAllocatorContiguousRangeContraint()]

    def __str__(self):
        return "{} with {} atoms".format(self._label, self.n_atoms)

    def __repr__(self):
        return self.__str__()
