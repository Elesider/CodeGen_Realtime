#pragma once

// 2019 ESTS, pp.375-376, Fig.16/19. Published: 50 ns, 100 kHz,
// +/-6 kV DC bus lowered to one third. Times and AC peaks are read from plots.
// PI settings, startup, carrier shape and phase are NOT published.
namespace paper {
constexpr double dt = 50e-9, carrier_hz = 100000;
constexpr double fundamental_hz = 60; // inferred, not explicitly stated
constexpr double control_dt = 10e-6; // reconstruction
constexpr double kp = .2, ki = 600, filter_tau = .0002; // reconstruction
struct Case { const char* name; bool pi; double duration, event, view_start, view_end; };
constexpr Case fig16 = {"fig16", false, .6, .5, .47, .58};
constexpr Case fig19 = {"fig19", true, 10.2, 10.133, 10.09, 10.2};
}
