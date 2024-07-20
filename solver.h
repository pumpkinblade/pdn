#ifndef __SOLVER_H__
#define __SOLVER_H__

#include "circuit.h"

struct OperatingPointSolution {
  GraphT::NodeMap<double> nodeVoltageMap;

  OperatingPointSolution(const GraphT &graph) : nodeVoltageMap(graph) {}
};

class OperatingPointSolver {
public:
  OperatingPointSolver(std::shared_ptr<Circuit> circuit) : m_ckt(circuit) {
    m_sln = std::make_shared<OperatingPointSolution>(circuit->graph);
  }

  void run();

  std::shared_ptr<OperatingPointSolution> solution() const { return m_sln; }

private:
  std::shared_ptr<Circuit> m_ckt;
  std::shared_ptr<OperatingPointSolution> m_sln;
};

#endif
