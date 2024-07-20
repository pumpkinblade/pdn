#include "solver.h"
#include "utils.h"
#include <Eigen/Dense>
#include <Eigen/SparseCore>

void OperatingPointSolver::run() {
  for (GraphT::NodeIt u(m_ckt->graph); u != lemon::INVALID; ++u) {
    int uId = m_ckt->graph.id(u);
    if (uId == 0) // skip gnd node
      continue;
    for (GraphT::OutArcIt oa(m_ckt->graph, u); oa != lemon::INVALID; ++oa) {
      int vId = m_ckt->graph.id(m_ckt->graph.target(oa));
      auto comp = m_ckt->arcCompMap[oa];
      switch (comp.type) {
      case PassiveComponentType::V:
        break;
      case PassiveComponentType::I:
        break;
      case PassiveComponentType::R:
        break;
      case PassiveComponentType::L:
        break;
      case PassiveComponentType::C:
        break;
      }
    }
    for (GraphT::InArcIt ia(m_ckt->graph, u); ia != lemon::INVALID; ++ia) {
      int vId = m_ckt->graph.id(m_ckt->graph.source(ia));
      auto comp = m_ckt->arcCompMap[ia];
      TODO();
    }
  }
}
