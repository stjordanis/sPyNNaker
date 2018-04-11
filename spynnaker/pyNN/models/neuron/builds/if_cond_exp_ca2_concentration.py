from spynnaker.pyNN.models.neuron import AbstractPopulationVertex
from spynnaker.pyNN.models.neuron.neuron_models \
    import NeuronModelLeakyIntegrateAndFire
from spynnaker.pyNN.models.neuron.synapse_types import SynapseTypeExponential
from spynnaker.pyNN.models.neuron.input_types import InputTypeConductance
from spynnaker.pyNN.models.neuron.threshold_types import ThresholdTypeStatic
from spynnaker.pyNN.models.neuron.additional_inputs \
    import AdditionalInputCa2Concentration

# global objects
DEFAULT_MAX_ATOMS_PER_CORE = 255


class IFCondExpCa2Concentration(AbstractPopulationVertex):
    """
    // Model from Braeder, J., Senn, W., and Fusi, S.: Learning Real-World
    // Stimuli in a Neural Network with Spike-Driven Synaptic Dynamics, Journal of
    // Neural Computation, 2007
    """

    _model_based_max_atoms_per_core = 255

    default_parameters = {
        'tau_m': 20.0, 'cm': 1.0, 'v_rest': -65.0, 'v_reset': -65.0,
        'v_thresh': -50.0, 'tau_syn_E': 5.0, 'tau_syn_I': 5.0,
        'tau_refrac': 0.1, 'i_offset': 0,
        'tau_ca2': 50.0, "i_ca2": 0.0, "i_alpha": 0.1, 'isyn_exc': 0.0,
        'isyn_inh': 0.0,
        'e_rev_E': 0.0, 'e_rev_I': -70.0}

    initialize_parameters  = {'v_init': None}

    def __init__(
            self, n_neurons, spikes_per_second=AbstractPopulationVertex.
            non_pynn_default_parameters['spikes_per_second'],
            ring_buffer_sigma=AbstractPopulationVertex.
            non_pynn_default_parameters['ring_buffer_sigma'],
            incoming_spike_buffer_size=AbstractPopulationVertex.
            non_pynn_default_parameters['incoming_spike_buffer_size'],
            constraints=AbstractPopulationVertex.non_pynn_default_parameters[
                'constraints'],
            label=AbstractPopulationVertex.non_pynn_default_parameters[
                'label'],
            tau_m=default_parameters['tau_m'], cm=default_parameters['cm'],
            v_rest=default_parameters['v_rest'],
            v_reset=default_parameters['v_reset'],
            v_thresh=default_parameters['v_thresh'],
            tau_syn_E=default_parameters['tau_syn_E'],
            tau_syn_I=default_parameters['tau_syn_I'],
            tau_refrac=default_parameters['tau_refrac'],
            i_offset=default_parameters['i_offset'],
            tau_ca2=default_parameters["tau_ca2"],
            i_ca2=default_parameters["i_ca2"],
            i_alpha=default_parameters["i_alpha"],
            v_init=initialize_parameters['v_init'],
            isyn_exc=default_parameters['isyn_exc'],
            isyn_inh=default_parameters['isyn_inh'],
            e_rev_E=default_parameters['e_rev_E'],
            e_rev_I=default_parameters['e_rev_I']):

        neuron_model = NeuronModelLeakyIntegrateAndFire(
            n_neurons, v_init, v_rest, tau_m, cm, i_offset,
            v_reset, tau_refrac)
        synapse_type = SynapseTypeExponential(
            n_neurons, tau_syn_E, tau_syn_I, initial_input_exc=isyn_exc,
            initial_input_inh=isyn_inh)
        input_type = InputTypeConductance(n_neurons, e_rev_E, e_rev_I)
        threshold_type = ThresholdTypeStatic(n_neurons, v_thresh)
        additional_input = AdditionalInputCa2Concentration(
            n_neurons, tau_ca2, i_ca2, i_alpha)

        super(IFCondExpCa2Concentration, self).__init__(
            n_neurons=n_neurons, binary="IF_cond_exp_ca2_concentration.aplx",
            label=label,
            max_atoms_per_core=(
                IFCondExpCa2Concentration._model_based_max_atoms_per_core),
            spikes_per_second=spikes_per_second,
            ring_buffer_sigma=ring_buffer_sigma,
            incoming_spike_buffer_size=incoming_spike_buffer_size,
            model_name="IF_cond_exp_ca2_concentration", neuron_model=neuron_model,
            input_type=input_type, synapse_type=synapse_type,
            threshold_type=threshold_type, additional_input=additional_input,
            constraints=constraints)

    @staticmethod
    def get_max_atoms_per_core():
        return IFCondExpCa2Concentration._model_based_max_atoms_per_core

    @staticmethod
    def set_max_atoms_per_core(new_value=DEFAULT_MAX_ATOMS_PER_CORE):
        IFCondExpCa2Concentration._model_based_max_atoms_per_core = new_value

