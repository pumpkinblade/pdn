#pragma once

#include "Branch.hpp"
#include <lemon/maps.h>
#include <lemon/smart_graph.h>

class Circuit {
  using GraphT = lemon::SmartDigraph;

public:
  Circuit();

  void report() const;

protected:
  GraphT::Node ensureNode(const std::string &node_name);
  GraphT::Arc connect(GraphT::Node n1, GraphT::Node n2, const Branch &branch);

protected:
  GraphT m_graph;
  lemon::CrossRefMap<GraphT, GraphT::Node, std::string> m_node_map;
  GraphT::ArcMap<Branch> m_branch_map;
  std::vector<std::tuple<int, int, std::string>> m_layer_comments;
};
