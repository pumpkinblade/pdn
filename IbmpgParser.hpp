#pragma once

#include "PowerGrid.hpp"
#include <lemon/maps.h>
#include <lemon/smart_graph.h>
#include <set>
#include <string>

class IbmpgParser {
  using GR = lemon::SmartDigraph;

public:
  IbmpgParser(const std::string &file_path);
  void makeComponent(char *comp_name, char *node1_name, char *node2_name,
                     double v);
  void makeComment(char *comment);

  void extractPowerGrid(PowerGridDesc &grid_desc);

private:
  void ensureNode(const std::string &node_name);

private:
  GR m_graph;
  lemon::CrossRefMap<GR, GR::Node, std::string> m_node_name_map;
  lemon::CrossRefMap<GR, GR::Arc, std::string> m_arc_name_map;
  GR::ArcMap<double> m_arc_value_map;
  std::set<int> m_vdd_net_id_set;
  std::set<int> m_vss_net_id_set;
};
