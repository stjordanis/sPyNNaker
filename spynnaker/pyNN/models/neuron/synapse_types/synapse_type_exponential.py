from spynnaker.pyNN.models.neural_properties.neural_parameter \
    import NeuronParameter
from spynnaker.pyNN.models.neuron.synapse_types.abstract_synapse_type \
    import AbstractSynapseType

from data_specification.enums.data_type import DataType

import numpy


def get_exponential_decay_and_init(tau, machine_time_step):
    decay = numpy.exp(numpy.divide(-float(machine_time_step),
                                   numpy.multiply(1000.0, tau)))
    init = numpy.multiply(numpy.multiply(tau, numpy.subtract(1.0, decay)),
                          (1000.0 / float(machine_time_step)))
    scale = float(pow(2, 32))
    decay_scaled = numpy.multiply(decay, scale).astype("uint32")
    init_scaled = numpy.multiply(init, scale).astype("uint32")
    return decay_scaled, init_scaled


class SynapseTypeExponential(AbstractSynapseType):

    def __init__(self, machine_time_step, tau_syn_E, tau_syn_I):
        AbstractSynapseType.__init__(self)
        self._tau_syn_E = tau_syn_E
        self._tau_syn_I = tau_syn_I
        self._machine_time_step = machine_time_step

    def get_n_synapse_types(self):
        return 2

    def get_synapse_id_by_target(self, target):
        if target == "excitatory":
            return 0
        elif target == "inhibitory":
            return 1
        return None

    def get_synapse_targets(self):
        return "excitatory", "inhibitory"

    def get_n_synapse_type_parameters(self):
        return 4

    def get_synapse_type_parameters(self):
        e_decay, e_init = get_exponential_decay_and_init(
            self._tau_syn_E, self._machine_time_step)
        i_decay, i_init = get_exponential_decay_and_init(
            self._tau_syn_I, self._machine_time_step)

        return [
            NeuronParameter(e_decay, DataType.UINT32),
            NeuronParameter(e_init, DataType.UINT32),
            NeuronParameter(i_decay, DataType.UINT32),
            NeuronParameter(i_init, DataType.UINT32)
        ]

    def get_n_cpu_cycles_per_neuron(self):

        # A guess
        return 100