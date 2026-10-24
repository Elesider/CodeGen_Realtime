#include "pi_voltage_controller.hpp"

#include <array>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
using Controller = PiVoltageController;
using Config = Controller::Config;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

void near(double actual, double expected, double tolerance, const std::string& message) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance)
        throw std::runtime_error(message + ": actual=" + std::to_string(actual)
                                 + ", expected=" + std::to_string(expected));
}

template<class Function> void invalid(Function operation, const std::string& message) {
    try { operation(); }
    catch (const std::invalid_argument&) { return; }
    throw std::runtime_error(message);
}

std::array<double, 3> balanced(double peak, double angle = 0, double zeroSequence = 0) {
    const double pi = std::acos(-1.0);
    return {{peak * std::cos(angle) + zeroSequence,
             peak * std::cos(angle - 2*pi/3) + zeroSequence,
             peak * std::cos(angle + 2*pi/3) + zeroSequence}};
}

double update(Controller& controller, double reference, double peak, bool enabled = true,
              double angle = 0, double zeroSequence = 0) {
    const auto phases = balanced(peak, angle, zeroSequence);
    return controller.update(reference, phases[0], phases[1], phases[2], enabled);
}

void clarke_scaling_and_zero_sequence() {
    for (int n = 0; n < 40; ++n) {
        const double angle = .137 * n;
        for (double offset : {-10000.0, 0.0, 7777.0}) {
            const auto phases = balanced(4321.0, angle, offset);
            near(Controller::clarkeAmplitude(phases[0], phases[1], phases[2]), 4321.0, 2e-11,
                 "Clarke amplitude must be phase peak and reject zero sequence");
        }
    }
    near(Controller::clarkeAmplitude(777, 777, 777), 0, 0, "Pure zero sequence has zero amplitude");
}

void normalized_proportional_and_feedback_polarity() {
    Config config;
    config.filter_tau_s = 0;
    config.kp = .2;
    config.ki = 0;
    Controller controller(config);
    near(update(controller, 3000, 0), .1, 1e-14, "3000/6000 normalized proportional gain");
    near(controller.normalizedError(), .5, 1e-14, "Reference error is normalized by voltage base");
    const double below = update(controller, 4500, 3000);
    near(below, .05, 1e-14, "Positive voltage error increases modulation");
    const double above = update(controller, 1500, 3000);
    near(above, 0, 0, "Negative voltage error clamps modulation at zero");
    require(controller.normalizedError() < 0 && controller.saturated(), "Feedback polarity/lower saturation");
}

void sample_time_and_integral_units() {
    Config coarse;
    coarse.dt_s = 10e-6;
    coarse.filter_tau_s = 0;
    coarse.kp = 0;
    coarse.ki = 40;
    Config fine = coarse;
    fine.dt_s = coarse.dt_s / 2;
    Controller a(coarse), b(fine);
    for (int n = 0; n < 100; ++n) update(a, 1500, 0);
    for (int n = 0; n < 200; ++n) update(b, 1500, 0);
    const double expected = 40 * .25 * .001;
    near(a.integrator(), expected, 1e-14, "Integral equals Ki * normalized error * elapsed seconds");
    near(b.integrator(), expected, 1e-14, "Halving sample time preserves elapsed-time integral");
    near(a.modulation(), b.modulation(), 1e-14, "Sample-time scaling must not double integral gain");
}

void lpf_exact_step_and_common_mode() {
    Config config;
    config.kp = config.ki = 0;
    Controller plain(config), shifted(config);
    const double expectedCoefficient = 1 - std::exp(-config.dt_s / config.filter_tau_s);
    near(plain.filterCoefficient(), expectedCoefficient, 1e-15, "Exact sampled RC-filter coefficient");
    for (int n = 1; n <= 120; ++n) {
        update(plain, 6000, 4200, true, .13*n);
        update(shifted, 6000, 4200, true, .13*n, 1000);
        const double expected = 4200 * (1 - std::exp(-n*config.dt_s/config.filter_tau_s));
        near(plain.measuredAmplitude(), 4200, 2e-11, "Measured Clarke amplitude before LPF");
        near(plain.filteredAmplitude(), expected, 2e-10, "LPF starts at zero and follows exact step response");
        near(shifted.filteredAmplitude(), plain.filteredAmplitude(), 2e-11, "LPF rejects common-mode input");
    }
    Config noFilter = config;
    noFilter.filter_tau_s = 0;
    Controller bypass(noFilter);
    update(bypass, 6000, 1234);
    near(bypass.filteredAmplitude(), 1234, 1e-11, "Zero time constant bypasses the LPF");
}

void saturation_antiwindup_and_release() {
    Config config;
    config.filter_tau_s = 0;
    config.kp = 2;
    config.ki = 100;
    config.max_modulation = .9;
    Controller upper(config), lower(config);
    for (int n = 0; n < 10000; ++n) {
        near(update(upper, 6000, 0), .9, 0, "Upper modulation limit");
        near(update(lower, 0, 6000), 0, 0, "Lower modulation limit");
        near(upper.integrator(), 0, 0, "No integral accumulation into upper saturation");
        near(lower.integrator(), 0, 0, "No integral accumulation into lower saturation");
        require(upper.saturated() && lower.saturated(), "Saturation flags");
    }
    const double releasedUpper = update(upper, 1800, 0);
    require(releasedUpper > 0 && releasedUpper < .9 && !upper.saturated(),
            "Lower reference must immediately release upper saturation without stored windup");
    const double releasedLower = update(lower, 6600, 6000);
    require(releasedLower > 0 && releasedLower < .9 && !lower.saturated(),
            "Positive error must release lower saturation");

    Config integralConfig = config;
    integralConfig.kp = 0;
    Controller integrating(integralConfig);
    for (int n = 0; n < 100; ++n) update(integrating, 3000, 0);
    const double before = integrating.integrator();
    update(integrating, 3000, 6000);
    require(integrating.integrator() > 0 && integrating.integrator() < before,
            "Opposing error must unwind a previously charged integral");
}

void disable_reset_and_external_reference_softstart() {
    Config config;
    Controller reused(config), fresh(config);
    for (int n = 0; n < 200; ++n) update(reused, 6000, 2000);
    require(reused.integrator() != 0 && reused.filteredAmplitude() > 0, "Precondition: controller contains state");
    near(update(reused, 6000, 2000, false), 0, 0, "Disabled output is zero");
    near(reused.integrator(), 0, 0, "Disable resets integral");
    near(reused.filteredAmplitude(), 0, 0, "Disable resets measurement filter");
    near(reused.measuredAmplitude(), 0, 0, "Disable resets measured amplitude");
    near(reused.normalizedError(), 0, 0, "Disable resets error");
    require(!reused.saturated(), "Disable resets saturation flag");
    double previous = 0;
    for (int n = 1; n <= 200; ++n) {
        // The testbench, not the PI class, supplies this 2 ms reference ramp.
        const double reference = 6000 * n * config.dt_s / .002;
        const double value = update(reused, reference, 0);
        const double expected = update(fresh, reference, 0);
        near(value, expected, 1e-14, "Re-enable must restart with the same state as a fresh controller");
        require(value >= previous && value >= 0 && value <= 1, "External softstart stays bounded and rises");
        if (n == 1) require(value < .002, "No retained integral kick at softstart restart");
        previous = value;
    }
}

void independent_average_plant_closed_loop() {
    Config config;
    Controller controller(config);
    const double plantTimeConstant = .003;
    const double decay = std::exp(-config.dt_s / plantTimeConstant);
    double voltage = 0;
    double maxInitialSteadyError = 0, maxLowerSteadyError = 0, maxFinalSteadyError = 0;
    const double pi = std::acos(-1.0);
    for (int n = 0; n < 24000; ++n) {
        const double t = n * config.dt_s;
        double reference = t < .08 ? 6000 : (t < .16 ? 3000 : 4200);
        reference *= std::min(1.0, t / .002); // External 2 ms startup ramp.
        const double modulation = update(controller, reference, voltage, true, 2*pi*60*t, 300);
        require(std::isfinite(modulation) && modulation >= 0 && modulation <= 1,
                "Closed-loop modulation remains finite and bounded");
        // Independent first-order averaged converter: dV/dt=(K*m-V)/tau.
        // The exact held-input solution avoids reusing the PI's numerical scheme.
        // A gain disturbance at 0.12 s verifies rejection beyond reference tracking.
        const double plantGain = t < .12 ? 6000 : 5400;
        voltage = decay * voltage + (1-decay) * plantGain * modulation;
        require(std::isfinite(voltage) && voltage >= 0 && voltage <= 6000,
                "Independent plant remains finite and physically bounded");
        if (t >= .07 && t < .08) maxInitialSteadyError = std::max(maxInitialSteadyError, std::abs(voltage-6000));
        if (t >= .15 && t < .16) maxLowerSteadyError = std::max(maxLowerSteadyError, std::abs(voltage-3000));
        if (t >= .23) maxFinalSteadyError = std::max(maxFinalSteadyError, std::abs(voltage-4200));
    }
    require(maxInitialSteadyError < 10, "Startup reference tracking settles within 10 V");
    require(maxLowerSteadyError < 10, "Lower reference and gain disturbance settle within 10 V");
    require(maxFinalSteadyError < 10, "Raised reference settles within 10 V");
    near(controller.modulation(), 4200.0/5400.0, .002, "Integral supplies correct steady converter duty");
    std::cout << "    average-plant max settled errors (V): " << maxInitialSteadyError << ", "
              << maxLowerSteadyError << ", " << maxFinalSteadyError << '\n';
}

void invalid_configurations_and_measurements() {
    std::vector<Config> invalidConfigs;
    auto add = [&](const std::function<void(Config&)>& change) { Config config; change(config); invalidConfigs.push_back(config); };
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const double inf = std::numeric_limits<double>::infinity();
    add([](Config& c) { c.dt_s = 0; });
    add([](Config& c) { c.dt_s = -1e-5; });
    add([&](Config& c) { c.dt_s = nan; });
    add([](Config& c) { c.filter_tau_s = -1; });
    add([&](Config& c) { c.filter_tau_s = inf; });
    add([](Config& c) { c.kp = -1; });
    add([&](Config& c) { c.kp = nan; });
    add([](Config& c) { c.ki = -1; });
    add([&](Config& c) { c.ki = inf; });
    add([](Config& c) { c.voltage_base_V = 0; });
    add([&](Config& c) { c.voltage_base_V = inf; });
    add([](Config& c) { c.max_modulation = 0; });
    add([](Config& c) { c.max_modulation = 1.01; });
    add([&](Config& c) { c.max_modulation = nan; });
    for (const auto& config : invalidConfigs)
        invalid([&] { Controller controller(config); }, "Invalid PI configuration was accepted");
    Controller controller{Config{}};
    invalid([&] { controller.update(-1, 0, 0, 0, true); }, "Negative amplitude reference was accepted");
    invalid([&] { controller.update(nan, 0, 0, 0, true); }, "NaN amplitude reference was accepted");
    invalid([&] { controller.update(6000, inf, 0, 0, true); }, "Infinite phase voltage was accepted");
    invalid([&] { controller.update(6000, 0, nan, 0, true); }, "NaN phase voltage was accepted");
}
} // namespace

int main() {
    const std::vector<std::pair<const char*, void(*)()>> tests = {
        {"Clarke scaling and zero sequence", clarke_scaling_and_zero_sequence},
        {"Normalized proportional gain and feedback polarity", normalized_proportional_and_feedback_polarity},
        {"Integral units and controller sample time", sample_time_and_integral_units},
        {"LPF exact step and common mode", lpf_exact_step_and_common_mode},
        {"Saturation, antiwindup and release", saturation_antiwindup_and_release},
        {"Disable reset and external softstart", disable_reset_and_external_reference_softstart},
        {"Independent averaged plant closed-loop tracking", independent_average_plant_closed_loop},
        {"Invalid configurations and measurements", invalid_configurations_and_measurements},
    };
    int failures = 0;
    std::cout << std::setprecision(10);
    for (const auto& test : tests) {
        try { test.second(); std::cout << "PASS: " << test.first << '\n'; }
        catch (const std::exception& error) {
            ++failures;
            std::cerr << "FAIL: " << test.first << ": " << error.what() << '\n';
        }
    }
    std::cout << (tests.size()-failures) << '/' << tests.size() << " PI regressions passed\n";
    return failures == 0 ? 0 : 1;
}
