#ifndef SHIPBOARD_PI_VOLTAGE_CONTROLLER_HPP
#define SHIPBOARD_PI_VOLTAGE_CONTROLLER_HPP

#include <algorithm>
#include <cmath>
#include <stdexcept>

// Voltage-amplitude outer loop; the electrical solver runs independently at 50 ns.
// Call update once per PWM period with the three phase voltages averaged over
// the preceding period. Instantaneous fixed-carrier-phase samples would alias ripple.
class PiVoltageController
{
public:
    struct Config {
        double dt_s = 1e-5;
        double filter_tau_s = 2e-4;
        double kp = .2;
        double ki = 600;
        double voltage_base_V = 6000;
        double max_modulation = 1;
    };

    explicit PiVoltageController(const Config& config) : config_(config) {
        if (!std::isfinite(config.dt_s) || config.dt_s <= 0
            || !std::isfinite(config.filter_tau_s) || config.filter_tau_s < 0
            || !std::isfinite(config.kp) || config.kp < 0
            || !std::isfinite(config.ki) || config.ki < 0
            || !std::isfinite(config.voltage_base_V) || config.voltage_base_V <= 0
            || !std::isfinite(config.max_modulation) || config.max_modulation <= 0
            || config.max_modulation > 1)
            throw std::invalid_argument("Invalid PI voltage-controller configuration");
        filter_coefficient_ = config.filter_tau_s == 0 ? 1 : -std::expm1(-config.dt_s / config.filter_tau_s);
    }

    static double clarkeAmplitude(double va, double vb, double vc) {
        const double alpha = (2 * va - vb - vc) / 3;
        const double beta = (vb - vc) / std::sqrt(3.0);
        return std::hypot(alpha, beta);
    }

    void reset() {
        filtered_ = integral_ = modulation_ = error_ = measured_ = 0;
        saturated_ = false;
    }

    double update(double reference_V, double va, double vb, double vc, bool enabled) {
        if (!enabled) { reset(); return 0; }
        if (!std::isfinite(reference_V) || reference_V < 0 || !std::isfinite(va)
            || !std::isfinite(vb) || !std::isfinite(vc))
            throw std::invalid_argument("PI reference and measurements must be finite; reference must be nonnegative");
        measured_ = clarkeAmplitude(va, vb, vc);
        filtered_ += filter_coefficient_ * (measured_ - filtered_);
        error_ = (reference_V - filtered_) / config_.voltage_base_V;
        const double proposed = integral_ + config_.ki * config_.dt_s * error_;
        const double proposedOutput = config_.kp * error_ + proposed;
        // Conditional integration: allow recovery, block accumulation further into saturation.
        const bool blocked = (proposedOutput > config_.max_modulation && error_ > 0)
                          || (proposedOutput < 0 && error_ < 0);
        if (!blocked)
            integral_ = proposed;
        const double unlimited = config_.kp * error_ + integral_;
        modulation_ = std::max(0.0, std::min(config_.max_modulation, unlimited));
        saturated_ = blocked || unlimited < 0 || unlimited > config_.max_modulation;
        return modulation_;
    }

    double modulation() const { return modulation_; }
    double filteredAmplitude() const { return filtered_; }
    double measuredAmplitude() const { return measured_; }
    double integrator() const { return integral_; }
    double normalizedError() const { return error_; }
    double unlimitedModulation() const { return config_.kp * error_ + integral_; }
    double filterCoefficient() const { return filter_coefficient_; }
    bool saturated() const { return saturated_; }
    const Config& config() const { return config_; }

private:
    Config config_;
    double filter_coefficient_ = 1;
    double filtered_ = 0, integral_ = 0, modulation_ = 0, error_ = 0, measured_ = 0;
    bool saturated_ = false;
};

#endif
