/*

Copyright (C) 2019-2020 Matthew Milton

This file is part of the LB-LMC Solver C++ Code Generation Library, included in the
Open Real-Time Simulation (ORTiS) Framework.

LB-LMC Solver C++ Code Generation Library is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

LB-LMC Solver C++ Code Generation Library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with LB-LMC Solver C++ Code Generation Library.  If not, see <https://www.gnu.org/licenses/>.

*/

#ifndef LBLMC_BRIDGECONVERTER2LEGIDEALSWITCHES_HPP
#define LBLMC_BRIDGECONVERTER2LEGIDEALSWITCHES_HPP

#include <string>
#include <vector>

#include "codegen/components/Component.hpp"

namespace lblmc
{

/**
	\brief Two-leg ideal-switch bridge with a bipolar split DC bus.

	Terminals are P, G, N, A, B. The DC side has two capacitors and each of
	A/B has a series inductor and resistor. There is no unused third leg.
	The model retains the forward Euler integration and fixed DC companion
	conductance of BridgeConverter3LegIdealSwitches, including its conditional
	stability limits. Each enabled leg selects the positive rail when its gate
	is true and the negative rail otherwise. Disabling the complete bridge
	uses the same passive anti-parallel diode approximation as the three-leg
	model; it does not remove the inductors or force their currents to zero.
	Diode voltage comparisons and blocking voltages are referenced to G.
**/
class BridgeConverter2LegIdealSwitches : public Component
{
private:
	double DT;
	double CAP;
	double IND;
	double RES;
	unsigned int P, G, N, A, B;
	unsigned int source_id_P, source_id_N, source_id_A, source_id_B;

	constexpr static double CAP_CONDUCTANCE = 10000.0;
	constexpr static double IND_CONDUCTANCE = 0.0;

	static void validateParameters(double dt, double cap, double ind, double res);

public:
	explicit BridgeConverter2LegIdealSwitches(std::string comp_name);
	BridgeConverter2LegIdealSwitches(std::string comp_name, double dt, double cap, double ind, double res);
	BridgeConverter2LegIdealSwitches(const BridgeConverter2LegIdealSwitches& base) = default;

	inline std::string getType() const { return "BridgeConverter2LegIdealSwitches"; }
	inline unsigned int getNumberOfTerminals() const { return 5; }
	inline unsigned int getNumberOfSources() const { return 4; }

	void getSourceIds(std::vector<unsigned int>& ids) const;
	void getResistiveCompanionElements(std::vector<ResistiveCompanionElement>& elements) const;

	using Component::getTerminalConnections;
	void setTerminalConnections(unsigned int p, unsigned int g, unsigned int n, unsigned int a, unsigned int b);
	void setTerminalConnections(const std::vector<unsigned int>& term_ids);
	void getTerminalConnections(std::vector<unsigned int>& term_ids) const;

	void setParameters(double dt, double cap, double ind, double res);
	inline const double& getDT() const { return DT; }
	inline const double& getCapacitance() const { return CAP; }
	inline const double& getInductance() const { return IND; }
	inline const double& getResistance() const { return RES; }

	void setIntegrationMethod(std::string method);
	inline std::string getIntegrationMethod() const { return INTEGRATION_EULER_FORWARD; }
	inline std::vector<std::string> getSupportedInputs() const { return {"sw_ctrl", "sw_en"}; }
	inline std::vector<std::string> getSupportedOutputs() const
	{
		return {"cp_voltage", "cn_voltage", "la_current", "lb_current"};
	}

	void stampConductance(SystemConductanceGenerator& gen);
	void stampSources(SystemSourceVectorGenerator& gen);
	std::string generateParameters();
	std::string generateFields();
	std::string generateInputs();
	std::string generateOutputs(std::string output = "ALL");
	std::string generateOutputsUpdateBody(std::string output = "ALL");
	std::string generateUpdateBody();
};

} //namespace lblmc

#endif // LBLMC_BRIDGECONVERTER2LEGIDEALSWITCHES_HPP
