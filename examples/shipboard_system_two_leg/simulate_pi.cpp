// Matched single-inverter open-loop / voltage-amplitude PI experiments.
#include "config.hpp"
#include "solver_adapter.hpp"
#include "pi_voltage_controller.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    if (argc < 5 || argc > 9) {
        std::cerr << "Usage: simulate_pi pi|open duration event_time prefix [kp ki filter_tau disturbance]\n";
        return 1;
    }
    const std::string mode = argv[1], prefix = argv[4];
    const bool closedLoop = mode == "pi";
    const double duration = std::strtod(argv[2], nullptr), event = std::strtod(argv[3], nullptr);
    PiVoltageController::Config cfg;
    if (argc > 5) cfg.kp = std::strtod(argv[5], nullptr);
    if (argc > 6) cfg.ki = std::strtod(argv[6], nullptr);
    if (argc > 7) cfg.filter_tau_s = std::strtod(argv[7], nullptr);
    const bool disturbance = argc > 8 && std::string(argv[8]) == "1";
    if ((!closedLoop && mode != "open") || !std::isfinite(duration) || !std::isfinite(event)
        || duration <= 0 || event < .02 || event >= duration) return 1;
    if (!closedLoop) cfg.kp = cfg.ki = 0; // Same measurement pipeline, no shadow PI action.
    PiVoltageController controller(cfg);
    const double dt = DEMO_DT, gateDt = 50e-9, carrierHz = 100000, hz = 60;
    const std::int64_t gateEvery = std::llround(gateDt / dt);
    const std::int64_t pwmEvery = std::llround(cfg.dt_s / dt);
    const std::int64_t carrierTicks = 200, eventTick = std::llround(event / gateDt);
    const std::int64_t disturbanceTick = std::llround((event + .03) / gateDt);
    const std::int64_t steps = std::llround(duration / dt);
    const std::int64_t globalEvery = std::llround(100e-6 / dt), focusEvery = std::llround(2e-6 / dt);
    if (gateEvery < 1 || pwmEvery < 1 || std::abs(gateEvery * dt - gateDt) > 1e-18
        || std::abs(pwmEvery * dt - cfg.dt_s) > 1e-18) return 1;
    const double pi = std::acos(-1.0), start = .004;
    Sample s = {};
    bool dc[2][2] = {}, inv[6][3] = {}, enabled[8] = {};
    double duty = .5, carrier = 0, reference = 0, modulation = 0, otherModulation = 0;
    double sums[3] = {}, intervalMean[3] = {};
    std::int64_t meanCount = 0, activeControls = 0, saturatedControls = 0;
    std::ofstream csv(prefix + ".csv"), controls(prefix + "_control.csv");
    if (!csv || !controls) return 1;
    csv << std::setprecision(17)
        << "time_s,va_V,vb_V,vc_V,bus_pos_V,bus_neg_V,local_bus_pos_V,local_bus_neg_V,total_load_power_W,reference_V,measured_amplitude_V,filtered_amplitude_V,modulation,other_modulation,integrator,normalized_error,saturated,dcdc_duty\n";
    controls << std::setprecision(17)
        << "time_s,reference_V,measured_amplitude_V,filtered_amplitude_V,modulation,integrator,normalized_error,saturated,local_bus_span_V,dcdc_duty,pi_unlimited_modulation\n";
    auto save = [&](std::int64_t n) {
        double power = 0;
        for (int j = 36; j < 54; ++j) power += s.nodes[j] * s.nodes[j] / 7;
        csv << n * dt << ',' << s.nodes[36] << ',' << s.nodes[37] << ',' << s.nodes[38]
            << ',' << s.nodes[2] << ',' << s.nodes[18] << ',' << s.nodes[4] << ',' << s.nodes[20]
            << ',' << power << ',' << reference << ',' << controller.measuredAmplitude()
            << ',' << controller.filteredAmplitude() << ',' << modulation << ',' << otherModulation
            << ',' << controller.integrator() << ',' << controller.normalizedError()
            << ',' << controller.saturated() << ',' << duty << '\n';
    };
    save(0);
    std::string status = "completed";
    std::int64_t completed = 0;
    double maximum = 0;
    const auto begun = std::chrono::steady_clock::now();
    for (std::int64_t n = 1; n <= steps; ++n) {
        const std::int64_t stepStart = n - 1;
        const double tStart = stepStart * dt;
        if (stepStart % pwmEvery == 0) {
            if (meanCount) for (int phase = 0; phase < 3; ++phase) intervalMean[phase] = sums[phase] / meanCount;
            for (double& value : sums) value = 0;
            meanCount = 0;
            const double ramp = std::min(1.0, std::max(0.0, (tStart - start) / .002));
            reference = (stepStart / gateEvery >= eventTick ? 3000 : 6000) * ramp;
            const bool on = stepStart >= std::llround(start / dt);
            const double command = controller.update(reference, intervalMean[0], intervalMean[1], intervalMean[2], on);
            modulation = closedLoop ? command : reference / cfg.voltage_base_V;
            if (on) { ++activeControls; if (controller.saturated()) ++saturatedControls; }
        }
        if (stepStart % gateEvery == 0) {
            const std::int64_t tick = stepStart / gateEvery;
            carrier = (tick % carrierTicks) / static_cast<double>(carrierTicks);
            const double dcRamp = std::min(1.0, std::max(0.0, (tStart - 20e-6) / .002));
            duty = .5 + ((disturbance && tick >= disturbanceTick ? .75 : .8) - .5) * dcRamp;
            for (int k = 0; k < 2; ++k) {
                enabled[k] = tStart >= 20e-6;
                dc[k][0] = carrier < duty;
                dc[k][1] = !dc[k][0];
            }
            otherModulation = std::min(1.0, std::max(0.0, (tStart - start) / .002));
            for (int phase = 0; phase < 3; ++phase) {
                const double sine = std::sin(2 * pi * hz * tStart - 2 * pi * phase / 3);
                for (int k = 0; k < 6; ++k) {
                    enabled[k + 2] = tStart >= start;
                    inv[k][phase] = carrier < .5 * (1 + (k == 0 ? modulation : otherModulation) * sine);
                }
            }
        }
        if (stepStart % pwmEvery == 0 && (stepStart % globalEvery == 0 || (tStart >= event - .043 && tStart <= event + .067)))
            controls << tStart << ',' << reference << ',' << controller.measuredAmplitude() << ','
                     << controller.filteredAmplitude() << ',' << modulation << ',' << controller.integrator()
                     << ',' << controller.normalizedError() << ',' << controller.saturated()
                     << ',' << s.nodes[4] - s.nodes[20] << ',' << duty << ',' << controller.unlimitedModulation() << '\n';
        advance(s, dc, inv, enabled);
        for (int phase = 0; phase < 3; ++phase) sums[phase] += s.nodes[36 + phase];
        ++meanCount;
        completed = n;
        bool nonfinite = !std::isfinite(s.nodes[2]) || !std::isfinite(s.nodes[18]) || !std::isfinite(s.nodes[36]);
        if (n % 100 == 0 || n < 2000 || n == steps || nonfinite) {
            for (int j = 0; j < 54; ++j) {
                nonfinite = nonfinite || !std::isfinite(s.nodes[j]) || !std::isfinite(s.outputs[j]);
                if (std::isfinite(s.nodes[j])) maximum = std::max(maximum, std::abs(s.nodes[j]));
            }
        }
        if (nonfinite) status = "nonfinite";
        else if (maximum > 1e8) status = "voltage_guard";
        const double t = n * dt;
        if (n % globalEvery == 0 || (t >= event - .043 && t <= event + .067 && n % focusEvery == 0)
            || (t <= .03 && n % pwmEvery == 0) || std::abs(t - event) < 50e-6 || n < 1000 || n == steps || status != "completed") save(n);
        if (status != "completed") break;
    }
    const double wall = std::chrono::duration<double>(std::chrono::steady_clock::now() - begun).count();
    std::ofstream json(prefix + ".json");
    json << std::setprecision(17)
         << "{\n\"mode\":\"" << mode << "\",\n\"status\":\"" << status << "\",\n\"dt_s\":" << dt
         << ",\n\"duration_s\":" << duration << ",\n\"event_time_s\":" << event << ",\n\"last_time_s\":" << completed * dt
         << ",\n\"completed_steps\":" << completed << ",\n\"wall_seconds\":" << wall
         << ",\n\"maximum_checked_voltage_V\":" << maximum << ",\n\"controller_dt_s\":" << cfg.dt_s
         << ",\n\"kp\":" << cfg.kp << ",\n\"ki_per_s\":" << cfg.ki << ",\n\"filter_tau_s\":" << cfg.filter_tau_s
         << ",\n\"voltage_base_V\":" << cfg.voltage_base_V << ",\n\"maximum_modulation\":" << cfg.max_modulation
         << ",\n\"active_control_updates\":" << activeControls << ",\n\"saturated_control_updates\":" << saturatedControls
         << ",\n\"controlled_inverter\":1,\n\"other_inverters_modulation\":1,\n\"carrier_Hz\":100000,\n\"fundamental_Hz_assumed\":60"
         << ",\n\"disturbance_enabled\":" << (disturbance ? "true" : "false")
         << ",\n\"disturbance_time_s\":" << event + .03
         << ",\n\"measurement\":\"Clarke magnitude of previous PWM-period mean phase voltages, then first-order LPF\",\n\"feedforward\":false,\n\"header_postprocessing\":false\n}\n";
    std::cout << prefix << ": " << status << ", t=" << completed * dt << ", wall=" << wall << "s\n";
    return status == "completed" ? 0 : 2;
}
