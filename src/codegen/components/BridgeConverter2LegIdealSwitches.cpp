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

#include "codegen/components/BridgeConverter2LegIdealSwitches.hpp"
#include "codegen/SystemConductanceGenerator.hpp"
#include "codegen/SystemSourceVectorGenerator.hpp"
#include "codegen/ArrayObject.hpp"
#include "codegen/Object.hpp"

#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace lblmc
{

BridgeConverter2LegIdealSwitches::BridgeConverter2LegIdealSwitches(std::string comp_name) :
	BridgeConverter2LegIdealSwitches(comp_name, 1.0, 1.0, 1.0, 1.0)
{}

BridgeConverter2LegIdealSwitches::BridgeConverter2LegIdealSwitches
(
	std::string comp_name,
	double dt,
	double cap,
	double ind,
	double res
) :
	Component(comp_name),
	DT(dt), CAP(cap), IND(ind), RES(res),
	P(0), G(0), N(0), A(0), B(0),
	source_id_P(0), source_id_N(0), source_id_A(0), source_id_B(0)
{
	if(comp_name.empty())
		throw std::invalid_argument("BridgeConverter2LegIdealSwitches: comp_name must be non-empty");
	validateParameters(dt, cap, ind, res);
}

void BridgeConverter2LegIdealSwitches::validateParameters(double dt, double cap, double ind, double res)
{
	if(!std::isfinite(dt) || dt <= 0.0 || !std::isfinite(cap) || cap <= 0.0 ||
		!std::isfinite(ind) || ind <= 0.0 || !std::isfinite(res) || res < 0.0)
	{
		throw std::invalid_argument("BridgeConverter2LegIdealSwitches: dt, cap, and ind must be finite and positive; res must be finite and nonnegative");
	}
}

void BridgeConverter2LegIdealSwitches::setParameters(double dt, double cap, double ind, double res)
{
	validateParameters(dt, cap, ind, res);
	DT = dt;
	CAP = cap;
	IND = ind;
	RES = res;
}

void BridgeConverter2LegIdealSwitches::setIntegrationMethod(std::string method)
{
	if(method != INTEGRATION_EULER_FORWARD)
		throw std::invalid_argument("BridgeConverter2LegIdealSwitches: only euler_forward integration is supported");
}

void BridgeConverter2LegIdealSwitches::setTerminalConnections
(
	unsigned int p, unsigned int g, unsigned int n, unsigned int a, unsigned int b
)
{
	P = p;
	G = g;
	N = n;
	A = a;
	B = b;
}

void BridgeConverter2LegIdealSwitches::setTerminalConnections(const std::vector<unsigned int>& term_ids)
{
	if(term_ids.size() != 5)
		throw std::invalid_argument("BridgeConverter2LegIdealSwitches: exactly five terminals P, G, N, A, B are required");
	setTerminalConnections(term_ids[0], term_ids[1], term_ids[2], term_ids[3], term_ids[4]);
}

void BridgeConverter2LegIdealSwitches::getTerminalConnections(std::vector<unsigned int>& term_ids) const
{
	term_ids = {P, G, N, A, B};
}

void BridgeConverter2LegIdealSwitches::getSourceIds(std::vector<unsigned int>& ids) const
{
	ids = {source_id_P, source_id_N, source_id_A, source_id_B};
}

void BridgeConverter2LegIdealSwitches::getResistiveCompanionElements
(
	std::vector<ResistiveCompanionElement>& elements
) const
{
	elements.clear();
	elements.push_back(RCE{appendName("bpos"), P, G, 0.0, CAP_CONDUCTANCE, source_id_P, false, false, false});
	elements.push_back(RCE{appendName("bneg"), N, G, 0.0, CAP_CONDUCTANCE, source_id_N, false, false, false});
	elements.push_back(RCE{appendName("bout1"), A, G, 0.0, IND_CONDUCTANCE, source_id_A, false, false, false});
	elements.push_back(RCE{appendName("bout2"), B, G, 0.0, IND_CONDUCTANCE, source_id_B, false, false, false});
}

void BridgeConverter2LegIdealSwitches::stampConductance(SystemConductanceGenerator& gen)
{
	gen.stampConductance(CAP_CONDUCTANCE, P, G);
	gen.stampConductance(CAP_CONDUCTANCE, N, G);
	gen.stampConductance(IND_CONDUCTANCE, A, G);
	gen.stampConductance(IND_CONDUCTANCE, B, G);
}

void BridgeConverter2LegIdealSwitches::stampSources(SystemSourceVectorGenerator& gen)
{
	source_id_P = gen.insertSource(P, G);
	source_id_N = gen.insertSource(N, G);
	source_id_A = gen.insertSource(A, G);
	source_id_B = gen.insertSource(B, G);
}

std::string BridgeConverter2LegIdealSwitches::generateParameters()
{
	const double HOC = DT/CAP;
	const double HOL = DT/IND;
	std::stringstream sstrm;
	sstrm << std::setprecision(16) << std::scientific;
	generateParameter(sstrm, "DT", DT);
	generateParameter(sstrm, "CAP", CAP);
	generateParameter(sstrm, "IND", IND);
	generateParameter(sstrm, "RES", RES);
	generateParameter(sstrm, "HOC", HOC);
	generateParameter(sstrm, "HOL", HOL);
	generateParameter(sstrm, "CAP_CONDUCTANCE", CAP_CONDUCTANCE);
	generateParameter(sstrm, "IND_CONDUCTANCE", IND_CONDUCTANCE);
	return sstrm.str();
}

std::string BridgeConverter2LegIdealSwitches::generateFields()
{
	std::stringstream sstrm;
	sstrm << std::setprecision(16) << std::scientific;
	for(const auto& field : {"vc1", "vc2", "il1", "il2"})
		generatePersistentField(sstrm, field, 0.0);
	return sstrm.str();
}

std::string BridgeConverter2LegIdealSwitches::generateInputs()
{
	ArrayObject sw_ctrl("bool", appendName("sw_ctrl"), "", {2});
	Object sw_en("bool", appendName("sw_en"), "");
	return sw_ctrl.generateArgument() + ",\n" + sw_en.generateArgument();
}

std::string BridgeConverter2LegIdealSwitches::generateOutputs(std::string output)
{
	std::stringstream sstrm;
	bool first = true;
	for(const auto& field : getSupportedOutputs())
	{
		if(output != "ALL" && output != field)
			continue;
		if(!first)
			sstrm << ",\n";
		Object signal("real*", appendName(field), "");
		sstrm << signal.generateArgument();
		first = false;
	}
	return sstrm.str();
}

std::string BridgeConverter2LegIdealSwitches::generateOutputsUpdateBody(std::string output)
{
	std::stringstream sstrm;
	const auto outputs = getSupportedOutputs();
	const char* fields[] = {"vc1", "vc2", "il1", "il2"};
	for(unsigned int i = 0; i < outputs.size(); ++i)
	{
		if(output == "ALL" || output == outputs[i])
			sstrm << "*" << appendName(outputs[i]) << " = " << appendName(fields[i]) << ";\n";
	}
	return sstrm.str();
}

std::string BridgeConverter2LegIdealSwitches::generateUpdateBody()
{
	std::stringstream sstrm;
	const auto name = [this](const std::string& field) { return appendName(field); };
	const unsigned int terminals[] = {P, G, N, A, B};
	const char* voltage_fields[] = {"epos_past", "eneu_past", "eneg_past", "eout1_past", "eout2_past"};
	for(unsigned int i = 0; i < 5; ++i)
		sstrm << "real " << name(voltage_fields[i]) << " = x[" << terminals[i] << "];\n";
	for(const auto& field : {"vc1", "vc2", "il1", "il2"})
		sstrm << "real " << name(std::string(field) + "_past") << " = " << name(field) << ";\n";

	// Emit the same rail/diode selection for each of the two real output legs.
	for(unsigned int leg = 1; leg <= 2; ++leg)
	{
		const std::string number = std::to_string(leg);
		const std::string current = name("il" + number + "_past");
		const std::string voltage = name("eout" + number + "_past");
		const std::string relative_voltage = name("eout" + number + "_to_neutral");
		const std::string selected = name("selected" + number);
		const std::string positive = name("a" + number);
		const std::string negative = name("b" + number);
		// Internal capacitor voltages are relative to G, including diode blocking.
		// This preserves the grounded-G equations and also handles a floating G.
		sstrm << "real " << relative_voltage << " = " << voltage << " - " << name("eneu_past") << ";\n";
		sstrm << "real " << selected << ", " << positive << ", " << negative << ";\n";
		sstrm << "if(" << name("sw_en") << ")\n{\n";
		sstrm << "\tif(" << name("sw_ctrl") << "[" << leg-1 << "])\n\t{\n";
		sstrm << "\t\t" << selected << " = " << name("vc1_past") << ";\n";
		sstrm << "\t\t" << positive << " = " << current << ";\n";
		sstrm << "\t\t" << negative << " = real(0.0);\n\t}\n\telse\n\t{\n";
		sstrm << "\t\t" << selected << " = " << name("vc2_past") << ";\n";
		sstrm << "\t\t" << positive << " = real(0.0);\n";
		sstrm << "\t\t" << negative << " = " << current << ";\n\t}\n}\nelse\n{\n";
		sstrm << "\tif(" << current << " > real(0.0))\n\t{\n";
		sstrm << "\t\t" << selected << " = " << name("vc2_past") << ";\n";
		sstrm << "\t\t" << positive << " = real(0.0);\n";
		sstrm << "\t\t" << negative << " = " << current << ";\n\t}\n";
		sstrm << "\telse if(" << current << " < real(0.0) || " << relative_voltage << " > " << name("vc1_past") << ")\n\t{\n";
		sstrm << "\t\t" << selected << " = " << name("vc1_past") << ";\n";
		sstrm << "\t\t" << positive << " = " << current << ";\n";
		sstrm << "\t\t" << negative << " = real(0.0);\n\t}\n";
		sstrm << "\telse if(" << relative_voltage << " < " << name("vc2_past") << ")\n\t{\n";
		sstrm << "\t\t" << selected << " = " << name("vc2_past") << ";\n";
		sstrm << "\t\t" << positive << " = real(0.0);\n";
		sstrm << "\t\t" << negative << " = " << current << ";\n\t}\n\telse\n\t{\n";
		sstrm << "\t\t" << selected << " = " << relative_voltage << ";\n";
		sstrm << "\t\t" << positive << " = real(0.0);\n";
		sstrm << "\t\t" << negative << " = real(0.0);\n\t}\n}\n";
	}

	sstrm << "real " << name("ipos") << " = " << name("CAP_CONDUCTANCE") << "*(" << name("epos_past") << " - " << name("vc1_past") << " - " << name("eneu_past") << ");\n";
	sstrm << "real " << name("ineg") << " = " << name("CAP_CONDUCTANCE") << "*(" << name("eneg_past") << " - " << name("vc2_past") << " - " << name("eneu_past") << ");\n";
	for(unsigned int leg = 1; leg <= 2; ++leg)
	{
		const std::string number = std::to_string(leg);
		sstrm << name("il" + number) << " = " << name("il" + number + "_past") << " + " << name("HOL") << "*(" << name("selected" + number) << " + " << name("eneu_past") << " - " << name("eout" + number + "_past") << " - " << name("RES") << "*" << name("il" + number + "_past") << ");\n";
	}
	sstrm << name("vc1") << " = " << name("vc1_past") << " + " << name("HOC") << "*(" << name("ipos") << " - " << name("a1") << " - " << name("a2") << ");\n";
	sstrm << name("vc2") << " = " << name("vc2_past") << " + " << name("HOC") << "*(" << name("ineg") << " - " << name("b1") << " - " << name("b2") << ");\n";
	const unsigned int source_ids[] = {source_id_P, source_id_N, source_id_A, source_id_B};
	const std::string contributions[] =
	{
		name("vc1") + "*" + name("CAP_CONDUCTANCE"),
		name("vc2") + "*" + name("CAP_CONDUCTANCE"),
		name("il1"), name("il2")
	};
	for(unsigned int i = 0; i < 4; ++i)
		sstrm << "b_components[" << source_ids[i]-1 << "] = " << contributions[i] << ";\n";
	return sstrm.str();
}

} //namespace lblmc
