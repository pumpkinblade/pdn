#include "Circuit.hpp"
#include <fmt/core.h>

Circuit::Circuit() : m_graph(), m_node_map(m_graph), m_branch_map(m_graph) {
  GraphT::Node gnd = m_graph.addNode();
  m_node_map.set(gnd, "0");
}

void Circuit::report() const {
  fmt::println("number of nodes: {}", m_graph.nodeNum());
  fmt::println("number of branchs: {}", m_graph.arcNum());
}

Circuit::GraphT::Node Circuit::ensureNode(const std::string &node_name) {
  if (m_node_map.count(node_name) == 0) {
    auto n = m_graph.addNode();
    m_node_map.set(n, node_name);
    return n;
  }
  return m_node_map(node_name);
}

Circuit::GraphT::Arc Circuit::connect(Circuit::GraphT::Node n1,
                                      Circuit::GraphT::Node n2,
                                      const Branch &branch) {
  GraphT::Arc a = m_graph.addArc(n1, n2);
  m_branch_map.set(a, branch);
  return a;
}
