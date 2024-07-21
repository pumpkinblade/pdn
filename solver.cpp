#include "solver.h"
#include "utils.h"
#include <Eigen/SparseCore>
#include <Eigen/SparseLU>
#include <lemon/adaptors.h>

void OperatingPointSolver::run() {
  // capacitor -> open
  GraphT::ArcMap<bool> arcMaskMap(m_ckt->graph, true);
  for (GraphT::ArcIt a(m_ckt->graph); a != lemon::INVALID; ++a) {
    if (m_ckt->arcCompMap[a].type == PassiveComponentType::C) {
      arcMaskMap.set(a, false);
    }
  }
  auto g = lemon::subDigraph(m_ckt->graph, lemon::TrueMap<GraphT::Node>{},
                             arcMaskMap);
  // inductor -> short
  struct L2V0 {
    using argument_type = PassiveComponent;
    using result_type = PassiveComponent;
    PassiveComponent operator()(PassiveComponent comp) const {
      if (comp.type == PassiveComponentType::L) {
        return {PassiveComponentType::V, 0};
      }
      return comp;
    }
  };
  auto m = lemon::composeMap(lemon::FunctorToMap<L2V0>{}, m_ckt->arcCompMap);

  int nrV = g.nodeNum() - 1; // number of voltage variable
  int nrI = 0;               // number of current varaible
  GraphT::ArcMap<int> voltageSourceRowMap(m_ckt->graph);
  GraphT::Arc arc;
  for (g.first(arc); arc != lemon::INVALID; g.next(arc)) {
    if (m[arc].type == PassiveComponentType::V) {
      voltageSourceRowMap.set(arc, nrV + nrI);
      nrI++;
    }
  }

  // construct matrix
  std::vector<Eigen::Triplet<double>> triplets;
  Eigen::VectorXd vecI = Eigen::VectorXd::Zero(nrV + nrI);
  Eigen::SparseMatrix<double> matG(nrV + nrI, nrV + nrI);
  for (g.first(arc); arc != lemon::INVALID; g.next(arc)) {
    auto [type, value] = m[arc];
    auto s = g.id(g.source(arc));
    auto t = g.id(g.target(arc));

    switch (type) {
    case PassiveComponentType::V:
      if (s) {
        triplets.emplace_back(s - 1, voltageSourceRowMap[arc], 1);
        triplets.emplace_back(voltageSourceRowMap[arc], s - 1, 1);
      }
      if (t) {
        triplets.emplace_back(t - 1, voltageSourceRowMap[arc], -1);
        triplets.emplace_back(voltageSourceRowMap[arc], t - 1, -1);
      }
      vecI(voltageSourceRowMap[arc]) = value;
      break;
    case PassiveComponentType::I:
      if (s) {
        vecI(s - 1) -= value;
      }
      if (t) {
        vecI(t - 1) += value;
      }
      break;
    case PassiveComponentType::R:
      if (s & t) {
        triplets.emplace_back(s - 1, t - 1, -1 / value);
        triplets.emplace_back(t - 1, s - 1, -1 / value);
      }
      if (s) {
        triplets.emplace_back(s - 1, s - 1, 1 / value);
      }
      if (t) {
        triplets.emplace_back(t - 1, t - 1, 1 / value);
      }
      break;
    default:
      PANIC("unexpected component");
      break;
    }
  }
  matG.setFromTriplets(triplets.begin(), triplets.end());

  // solve using LU
  Eigen::SparseLU<Eigen::SparseMatrix<double>, Eigen::COLAMDOrdering<int>> lu;
  lu.analyzePattern(matG);
  lu.factorize(matG);
  Eigen::VectorXd sln = lu.solve(vecI);

  // commit solution
  m_sln->nodeVoltageMap.set(m_ckt->graph.nodeFromId(0), 0);
  for (int i = 0; i < nrV; i++) {
    m_sln->nodeVoltageMap.set(m_ckt->graph.nodeFromId(1 + i), sln(i));
  }
}
