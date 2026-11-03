// Fixed paper Fig.16 / Fig.19 experiments; standard C++17, CSV output only.
#include "config.hpp"
#include "paper_cases.hpp"
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
#include <filesystem>
#include <stdexcept>
namespace fs = std::filesystem;

template<int instance>
int simulate(const paper::Case& scenario, const fs::path& output)
{
    static_assert(DEMO_DT == paper::dt, "Solver must be generated at 50 ns");
    const bool closedLoop = scenario.pi;
    const std::string mode = closedLoop ? "pi" : "open";
    const std::string prefix = (output/scenario.name).string();
    const double duration = scenario.duration, event = scenario.event;
    const bool disturbance = false;
    PiVoltageController::Config cfg;
    cfg.dt_s = paper::control_dt;
    cfg.kp = paper::kp; cfg.ki = paper::ki; cfg.filter_tau_s = paper::filter_tau;
    std::cout << (closedLoop ? "[2/2] Fig.19: PI, 10.2 s" : "[1/2] Fig.16: DC bus, 0.6 s") << std::endl;
    PiVoltageController controller(cfg);
    const double dt = DEMO_DT, gateDt = paper::dt, hz = paper::fundamental_hz;
    const std::int64_t gateEvery = std::llround(gateDt / dt);
    const std::int64_t pwmEvery = std::llround(cfg.dt_s / dt);
    const std::int64_t carrierTicks = std::llround(1/(paper::carrier_hz*gateDt)), eventTick = std::llround(event / gateDt);
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
        if (closedLoop && stepStart % pwmEvery == 0) {
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
            duty = .5 + ((!closedLoop && tick >= eventTick ? .6 : .8) - .5) * dcRamp;
            for (int k = 0; k < 2; ++k) {
                enabled[k] = tStart >= 20e-6;
                dc[k][0] = carrier < duty;
                dc[k][1] = !dc[k][0];
            }
            otherModulation = std::min(1.0, std::max(0.0, (tStart - start) / .002));
            if (!closedLoop) { modulation = otherModulation; reference = 6000*otherModulation; }
            for (int phase = 0; phase < 3; ++phase) {
                const double sine = std::sin(2 * pi * hz * tStart - 2 * pi * phase / 3);
                for (int k = 0; k < 6; ++k) {
                    enabled[k + 2] = tStart >= start;
                    inv[k][phase] = carrier < .5 * (1 + (k == 0 ? modulation : otherModulation) * sine);
                }
            }
        }
        if (closedLoop && stepStart % pwmEvery == 0 && (stepStart % globalEvery == 0 || (tStart >= scenario.view_start && tStart <= scenario.view_end)))
            controls << tStart << ',' << reference << ',' << controller.measuredAmplitude() << ','
                     << controller.filteredAmplitude() << ',' << modulation << ',' << controller.integrator()
                     << ',' << controller.normalizedError() << ',' << controller.saturated()
                     << ',' << s.nodes[4] - s.nodes[20] << ',' << duty << ',' << controller.unlimitedModulation() << '\n';
        advance<instance>(s, dc, inv, enabled);
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
        if (n % globalEvery == 0 || (t >= scenario.view_start && t <= scenario.view_end && n % focusEvery == 0)
            || (t <= .03 && n % pwmEvery == 0) || std::abs(t - event) < 50e-6 || n < 1000 || n == steps || status != "completed") save(n);
        if (n % 20000000 == 0 || n == steps)
            std::cout << "  t=" << t << " / " << duration << " s" << std::endl;
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
         << ",\n\"measurement\":\"Clarke magnitude of previous PWM-period mean phase voltages, then first-order LPF\",\n\"pi_gains_published\":false,\"control_settings_origin\":\"reconstruction, not published in paper\",\"feedforward\":false,\n\"header_postprocessing\":false\n}\n";
    std::cout << prefix << ": " << status << ", t=" << completed * dt << ", wall=" << wall << "s\n";
    return status == "completed" ? 0 : 2;
}


int main(int argc, char** argv)
{
    try {
        if (argc != 1) throw std::runtime_error("No parameters required; run simulate_pi directly.");
        // Both the executable and copied Python script use this same results directory.
        const auto output = fs::absolute(argv[0]).parent_path()/"results";
        fs::create_directories(output);
        std::cout << "Fixed cases: Fig.16 / Fig.19; 50 ns; 100 kHz PWM.\n"
                  << "PI settings are reconstructed; 60 Hz is inferred from the paper plot.\n"
                  << "Output: " << output.string() << std::endl;
        if (simulate<0>(paper::fig16, output) != 0) throw std::runtime_error("Fig.16 simulation failed");
        if (simulate<1>(paper::fig19, output) != 0) throw std::runtime_error("Fig.19 simulation failed");
        std::cout << "CSV generation completed. Run plot_paper.py separately (no arguments).\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Failed: " << e.what() << '\n';
        return 1;
    }
}
