#ifndef _TIMING_PAIR_SUPERVISION_IMPL_H_
#define _TIMING_PAIR_SUPERVISION_IMPL_H_

//---------------------------------------
// Typedefines
//---------------------------------------

typedef int32_t post_trace_t; //[stdp | dopamine ]

typedef int16_t pre_trace_t;

#include "../synapse_structure/synapse_structure_weight_impl.h"
#include "timing.h"
//#include "../weight_dependence/weight_one_term.h"

// Include debug header for log_info etc
#include <debug.h>

// Include generic plasticity maths functions
#include "../../common/maths.h"
#include "../../common/stdp_typedefs.h"

//---------------------------------------
// Macros
//---------------------------------------
// Exponential decay lookup parameters
#define TAU_PLUS_TIME_SHIFT 0
#define TAU_PLUS_SIZE 256

#define TAU_MINUS_TIME_SHIFT 0
#define TAU_MINUS_SIZE 256

#define TAU_C_TIME_SHIFT 4
#define TAU_C_SIZE 520

#define TAU_D_TIME_SHIFT 2
#define TAU_D_SIZE 370


// Helper macros for looking up decays
#define DECAY_LOOKUP_TAU_PLUS(time) \
                maths_lut_exponential_decay( \
                    (time), TAU_PLUS_TIME_SHIFT, \
                    TAU_PLUS_SIZE, tau_plus_lookup)

#define DECAY_LOOKUP_TAU_MINUS(time) \
                maths_lut_exponential_decay( \
                    (time), TAU_MINUS_TIME_SHIFT, \
                    TAU_MINUS_SIZE, tau_minus_lookup)

#define DECAY_LOOKUP_TAU_C(time) \
                maths_lut_exponential_decay( \
                    (time), TAU_C_TIME_SHIFT, \
                    TAU_C_SIZE, tau_c_lookup)

#define DECAY_LOOKUP_TAU_D(time) \
                maths_lut_exponential_decay( \
                    (time), TAU_D_TIME_SHIFT, \
                    TAU_D_SIZE, tau_d_lookup)

//---------------------------------------
// Externals
//---------------------------------------
extern int16_t tau_plus_lookup[TAU_PLUS_SIZE];
extern int16_t tau_minus_lookup[TAU_MINUS_SIZE];
extern int16_t tau_c_lookup[TAU_C_SIZE];
extern int16_t tau_d_lookup[TAU_D_SIZE];
extern int32_t weight_update_constant_component;

// Trace get and set helper funtions
static inline int32_t get_post_trace(post_trace_t trace) {
    return (int32_t)(trace >> 16);
}

static inline int32_t get_dopamine_trace(post_trace_t trace) {
    return (int32_t)(trace & 0xFFFF);
}

static inline post_trace_t trace_build(int32_t post_trace, int32_t dopamine_trace) {
    return (post_trace_t)((((int16_t)(post_trace)) << 16) | ((int16_t)dopamine_trace));
//    return (post_trace_t)((post_trace << 16) | dopamine_trace);
}

//---------------------------------------
// Timing dependence inline functions
//---------------------------------------
static inline post_trace_t timing_get_initial_post_trace() {
    return (post_trace_t) 0;
}

//---------------------------------------
static inline post_trace_t timing_add_post_spike(
        uint32_t time, uint32_t last_time, post_trace_t last_trace) {

    // Get time since last spike
    uint32_t delta_time = time - last_time;

    // Decay previous post trace
    int32_t decayed_o1_trace = STDP_FIXED_MUL_16X16(get_post_trace(last_trace),
                                    DECAY_LOOKUP_TAU_MINUS(delta_time));

    // Add energy caused by new spike to trace
    // **NOTE** o2 trace is pre-multiplied by a3_plus
    int32_t new_o1_trace = decayed_o1_trace + STDP_FIXED_POINT_ONE;

    log_debug("\tdelta_time=%d, o1=%d\n", delta_time, new_o1_trace);

    // Decay previous dopamine trace
    int32_t new_dopamine_trace = STDP_FIXED_MUL_16X16(get_dopamine_trace(last_trace),
            DECAY_LOOKUP_TAU_D(delta_time));

    // Return new pre- synaptic event with decayed trace values with energy
    // for new spike added
    return (post_trace_t) trace_build(new_o1_trace, new_dopamine_trace);
}



//---------------------------------------
static inline pre_trace_t timing_add_pre_spike(
        uint32_t time, uint32_t last_time, pre_trace_t last_trace) {

    // Get time since last spike
    uint32_t delta_time = time - last_time;

    // Decay previous r1 and r2 traces
    int32_t decayed_r1_trace = STDP_FIXED_MUL_16X16(
        last_trace, DECAY_LOOKUP_TAU_PLUS(delta_time));

    // Add energy caused by new spike to trace
    int32_t new_r1_trace = decayed_r1_trace + STDP_FIXED_POINT_ONE;

    log_debug("\tdelta_time=%u, r1=%d\n", delta_time, new_r1_trace);

    // Return new pre-synaptic event with decayed trace values with energy
    // for new spike added
    return (pre_trace_t) new_r1_trace;
}


//---------------------------------------
//static inline update_state_t timing_apply_pre_spike(
//        uint32_t time, pre_trace_t trace, uint32_t last_pre_time,
//        pre_trace_t last_pre_trace, uint32_t last_post_time,
//        post_trace_t last_post_trace, update_state_t previous_state) {
//    use(time);
//    use(&trace);
//    use(last_pre_time);
//    use(last_pre_trace);
//    use(last_post_time);
//    use(&last_post_trace);
//
//    return previous_state;
//
//}
//
////---------------------------------------
//static inline update_state_t timing_apply_post_spike(
//        uint32_t time, post_trace_t trace, uint32_t last_pre_time,
//        pre_trace_t last_pre_trace, uint32_t last_post_time,
//        post_trace_t last_post_trace, update_state_t previous_state) {
//    use(time);
//    use(&trace);
//    use(last_pre_time);
//    use(last_pre_trace);
//    use(last_post_time);
//    use(&last_post_trace);
//
//
//    return previous_state;
//}


#endif // _TIMING_PAIR_IMPL_H_