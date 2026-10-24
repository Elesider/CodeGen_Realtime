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

#include "codegen/netlist/producers/BridgeConverter2LegIdealSwitchesProducer.hpp"
#include "codegen/components/BridgeConverter2LegIdealSwitches.hpp"

namespace lblmc
{

BridgeConverter2LegIdealSwitchesProducer::BridgeConverter2LegIdealSwitchesProducer() :
	ComponentProducer()
{
	type = "BridgeConverter2LegIdealSwitches";
	producer_name = "BridgeConverter2LegIdealSwitchesProducer";
	num_parameters = 4;
	num_terminals = 5;
}

std::unique_ptr<Component> BridgeConverter2LegIdealSwitchesProducer::operator()
(
	const ComponentListing& component_def
) const
{
	assertNetlistComponentInstanceValid(component_def);
	std::unique_ptr<BridgeConverter2LegIdealSwitches> comp(new BridgeConverter2LegIdealSwitches
	(
		component_def.getLabel(),
		component_def.getParameter(0),
		component_def.getParameter(1),
		component_def.getParameter(2),
		component_def.getParameter(3)
	));
	comp->setTerminalConnections
	(
		component_def.getTerminalConnection(0),
		component_def.getTerminalConnection(1),
		component_def.getTerminalConnection(2),
		component_def.getTerminalConnection(3),
		component_def.getTerminalConnection(4)
	);
	return std::unique_ptr<Component>(comp.release());
}

} //namespace lblmc
