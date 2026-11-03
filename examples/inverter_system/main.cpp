#include "ExampleInverterSystem.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <cmath>
#include <cstdint>
#include <iostream>

int main(int argc, char** argv) {
    try {
        if (argc != 1) throw std::runtime_error("Run without command-line arguments.");
        const auto output = std::filesystem::absolute(argv[0]).parent_path()/"results";
        std::filesystem::create_directories(output);
        std::ofstream csv(output/"inverter.csv"), pwm(output/"spwm.csv");
        if (!csv || !pwm) throw std::runtime_error("Cannot open inverter CSV files");
        csv << std::setprecision(17); pwm << std::setprecision(17);
        csv << "time_s,node1_voltage,node2_voltage,node3_voltage,node4_voltage,node5_voltage,ia_L_A,ib_L_A,ic_L_A\n"
            << "0,0,0,0,0,0,0,0,0\n";
        pwm << "time_s,reference_a,reference_b,reference_c,carrier,gate_a_upper,gate_a_lower\n";
        // Preserve the source example's physical settings, using C++17 throughout.
        constexpr double dt = 50e-9, duration = 1.0, hz = 50.0, carrier_hz = 100000.0, m = 1.0;
        const double pi = std::acos(-1.0);
        const std::int64_t steps = std::llround(duration/dt);
        const std::int64_t carrier_ticks = std::llround(1/(carrier_hz*dt));
        const std::int64_t zoom_start = std::llround(.022/dt), zoom_end = std::llround(.02205/dt);
        const std::int64_t steady_start = std::llround(.94/dt);
        double node[5] = {}, vcp = 0, vcn = 0, current[3] = {};
        bool gates[6] = {};
        for (std::int64_t n = 0; n < steps; ++n) {
            const double t = n*dt;
            const double u = (n % carrier_ticks)/static_cast<double>(carrier_ticks);
            const double carrier = 1-4*std::abs(u-.5);
            double reference[3];
            for (int phase = 0; phase < 3; ++phase) {
                reference[phase] = m*std::sin(2*pi*hz*t-2*pi*phase/3);
                gates[2*phase] = reference[phase] >= carrier;
                gates[2*phase+1] = !gates[2*phase];
            }
            if (n >= zoom_start && n <= zoom_end)
                pwm << t << ',' << reference[0] << ',' << reference[1] << ',' << reference[2] << ','
                    << carrier << ',' << gates[0] << ',' << gates[1] << '\n';
            ExampleInverterSystem_solver<0, double>(node, vcp, vcn, current[0], current[1], current[2], gates);
            for (double value : node)
                if (!std::isfinite(value) || std::abs(value) > 1e6) throw std::runtime_error("Invalid inverter voltage");
            for (double value : current)
                if (!std::isfinite(value)) throw std::runtime_error("Nonfinite inverter current");
            const auto completed = n+1;
            if (completed % 2000 == 0 || (completed >= steady_start && completed % 20 == 0) || completed == steps) {
                csv << completed*dt;
                // The generated interface has FIVE node outputs. Never read node[5].
                for (double value : node) csv << ',' << value;
                for (double value : current) csv << ',' << value;
                csv << '\n';
            }
        }
        csv.close(); pwm.close();
        if (!csv || !pwm) throw std::runtime_error("Failed to write inverter CSV");
        std::cout << "Completed 20000000 steps (50 ns, 1 s, 50 Hz, 100 kHz PWM).\nSaved: "
                  << output.string() << "\nRun plot.py separately.\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n'; return 1;
    }
}
