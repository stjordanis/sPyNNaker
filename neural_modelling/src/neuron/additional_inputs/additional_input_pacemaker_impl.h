#ifndef _ADDITIONAL_INPUT_PACEMAKER_H_
#define _ADDITIONAL_INPUT_PACEMAKER_H_

#include "additional_input.h"

//----------------------------------------------------------------------------
//----------------------------------------------------------------------------

typedef struct additional_input_t {

    // Pacemaker Current
    accum    I_H;
    accum    m;
    accum    m_inf;
    accum    e_to_t_on_tau_m_approx;
    accum    g_H; // max pacemaker conductance
    accum    E_H; // reversal potential
    accum    dt;

} additional_input_t;

static input_t additional_input_get_input_value_as_current(
        additional_input_pointer_t additional_input,
        state_t membrane_voltage) {

	additional_input->m_inf = 1 / (1 + expk((membrane_voltage+75)/5.5));

	additional_input->e_to_t_on_tau_m_approx = expk(-0.1 *
			((expk(-14.59 - 0.086 * membrane_voltage))
			+ expk(-1.87 + 0.0701 * membrane_voltage))
			);

	// Update m
	additional_input->m = additional_input->m_inf +
			(additional_input->m - additional_input->m_inf) *
			additional_input->e_to_t_on_tau_m_approx;

	// H is 1 and constant, so ignore - also not sure of activation gating power at present
	additional_input->I_H = // additional_input->g_H *
			0.001k *
			additional_input->m *
			(membrane_voltage - -65k); //additional_input->E_H);

	log_info("mem_V: %k, m: %k, m_inf: %k, tau_m: %k, I_H = %k",
			membrane_voltage,
			additional_input->m,
			additional_input->m_inf,
			additional_input->e_to_t_on_tau_m_approx,
			additional_input->I_H);

//    return additional_input->I_H;
    return additional_input->I_H;
}

static void additional_input_has_spiked(
        additional_input_pointer_t additional_input) {
	// no action to be taken on spiking
}

#endif // _ADDITIONAL_INPUT_PACEMAKER_H_
