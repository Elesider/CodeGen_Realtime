#include "RLC_Circuit.hpp"
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
        std::ofstream csv(output/"rlc.csv");
        if (!csv) throw std::runtime_error("Cannot open rlc.csv");
        csv << std::setprecision(17);
        csv << "time_s,v1_V,vc_V,il_A\n0,0,0,0\n";
        constexpr double dt = 50e-9, duration = 1.0;
        const std::int64_t steps = std::llround(duration/dt), save_every = 2000;
        double voltage[2] = {}, current = 0;
        for (std::int64_t n = 1; n <= steps; ++n) {
            RLC_Circuit_solver<0, double>(voltage, &current);
            if (!std::isfinite(voltage[0]) || !std::isfinite(voltage[1]) || !std::isfinite(current))
                throw std::runtime_error("Nonfinite RLC state");
            if (n % save_every == 0 || n == steps)
                csv << n*dt << ',' << voltage[0] << ',' << voltage[1] << ',' << current << '\n';
        }
        csv.close();
        if (!csv) throw std::runtime_error("Failed to write RLC CSV");
        std::cout << "Completed 20000000 steps (50 ns, 1 s).\nSaved: "
                  << (output/"rlc.csv").string() << "\nRun plot.py separately.\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n'; return 1;
    }
}
