#include "IbmpgParser.hpp"
#include <fmt/core.h>
#include <lemon/adaptors.h>
#include <lemon/bfs.h>
#include <regex>
#include <set>

IbmpgParser *pg = nullptr;
void yyset_in(FILE *);
int yyparse(void);
int yylex_destroy(void);

IbmpgParser::IbmpgParser(const std::string &file_path)
    : m_graph(), m_node_name_map(m_graph), m_arc_name_map(m_graph),
      m_arc_value_map(m_graph) {
  FILE *file = fopen(file_path.c_str(), "r");
  if (file == NULL) {
    fmt::println("unable to open spice file {}", file_path);
    return;
  }

  pg = this;
  yyset_in(file);
  int ret = yyparse();
  fclose(file);
  yylex_destroy();
  pg = nullptr;

  if (ret) {
    fmt::println("error occurred while parse spice netlist");
  }
}

void IbmpgParser::makeComponent(char *comp_name, char *node1_name,
                                char *node2_name, double v) {
  ensureNode(node1_name);
  ensureNode(node2_name);
  auto n1 = m_node_name_map(node1_name);
  auto n2 = m_node_name_map(node2_name);
  auto a = m_graph.addArc(n1, n2);
  m_arc_name_map.set(a, comp_name);
  m_arc_value_map.set(a, v);
  free(comp_name);
  free(node1_name);
  free(node2_name);
}

void IbmpgParser::makeComment(char *comment) {
  std::regex pattern("^\\* layer: \\w+,(\\w+) net: (\\d)+\n$");
  std::cmatch match;
  if (std::regex_match(comment, match, pattern)) {
    std::string net_name = match[1].str();
    int net_id = std::stoi(match[2].str());
    if (net_name == "GND") {
      m_vss_net_id_set.insert(net_id);
    } else {
      m_vdd_net_id_set.insert(net_id);
    }
  }
  free(comment);
}

void IbmpgParser::ensureNode(const std::string &node_name) {
  if (m_node_name_map.count(node_name) == 0) {
    auto n = m_graph.addNode();
    m_node_name_map.set(n, node_name);
  }
}

void IbmpgParser::extractPowerGrid(PowerGridDesc &grid_desc) {
  // extract vdd subgraph
  GR::Node gnd_node = m_node_name_map("0");
  GR::NodeMap<bool> is_vdd_map(m_graph, false);
  GR::NodeMap<std::pair<int, int>> pos_map(m_graph);
  GR::NodeMap<int> net_id_map(m_graph);
  is_vdd_map.set(gnd_node, true);
  std::regex regex_pattern("n(\\d+)_(\\d+)_(\\d+)$");
  std::smatch regex_match;
  for (GR::NodeIt n(m_graph); n != lemon::INVALID; ++n) {
    if (n == gnd_node)
      continue;
    const std::string &node_name = m_node_name_map[n];
    if (std::regex_search(node_name.cbegin(), node_name.cend(), regex_match,
                          regex_pattern)) {
      int net_id = std::stoi(regex_match[1].str());
      int x = std::stoi(regex_match[2].str());
      int y = std::stoi(regex_match[3].str());
      is_vdd_map.set(n, m_vdd_net_id_set.count(net_id) > 0);
      pos_map.set(n, std::make_pair(x, y));
      net_id_map.set(n, net_id);
    }
  }

  // // check connectivity
  // lemon::Undirector<SubGR> undirected_subgraph(subgraph);
  // lemon::Bfs<lemon::Undirector<SubGR>> bfs(undirected_subgraph);
  // bool connectivity = true;
  // bfs.run(gnd_node);
  // for (SubGR::NodeIt n(subgraph); n != lemon::INVALID; ++n) {
  //   if (!bfs.reached(n)) {
  //     connectivity = false;
  //     break;
  //   }
  // }
  // fmt::println("connectivity = {}", connectivity);

  // examine pitch
  using SubGR = lemon::FilterNodes<GR>;
  SubGR subgraph(m_graph, is_vdd_map);
  std::set<int> point_set_x, point_set_y;
  for (SubGR::NodeIt n(subgraph); n != lemon::INVALID; ++n) {
    if (n == gnd_node)
      continue;
    auto [x, y] = pos_map[n];
    point_set_x.insert(x);
    point_set_y.insert(y);
  }
  std::vector<int> points_x(point_set_x.begin(), point_set_x.end());
  std::vector<int> points_y(point_set_y.begin(), point_set_y.end());
  std::sort(points_x.begin(), points_x.end());
  std::sort(points_y.begin(), points_y.end());
  // fmt::println("[{}, {}] x [{}, {}]", points_x.front(), points_x.back(),
  //              points_y.front(), points_y.back());
  // fmt::println("size = {} x {} = {}", points_x.size(), points_y.size(),
  //              points_x.size() * points_y.size());

  grid_desc.grid.start_x = points_x.front();
  grid_desc.grid.start_y = points_y.front();
  grid_desc.grid.end_x = points_x.back();
  grid_desc.grid.end_y = points_y.back();
  grid_desc.grid.step_x = 0;
  grid_desc.grid.step_y = 0;
  for (size_t i = 1; i < points_x.size(); i++) {
    grid_desc.grid.step_x += points_x[i] - points_x[i - 1];
  }
  for (size_t i = 1; i < points_y.size(); i++) {
    grid_desc.grid.step_y += points_y[i] - points_y[i - 1];
  }
  grid_desc.grid.step_x /= (points_x.size() - 1);
  grid_desc.grid.step_y /= (points_y.size() - 1);

  // make resistor, load, pad
  grid_desc.wires.clear();
  grid_desc.pads.clear();
  grid_desc.loads.clear();
  for (SubGR::ArcIt a(subgraph); a != lemon::INVALID; ++a) {
    auto n1 = subgraph.source(a);
    auto n2 = subgraph.target(a);
    auto [x1, y1] = pos_map[n1];
    auto [x2, y2] = pos_map[n2];
    auto net_id1 = net_id_map[n1];
    auto net_id2 = net_id_map[n2];
    double v = m_arc_value_map[a];
    bool is_res = std::tolower(m_arc_name_map[a].front()) == 'r';
    bool is_current = std::tolower(m_arc_name_map[a].front()) == 'i';
    bool is_xy_res = is_res && (net_id1 == net_id2) &&
                     (n1 != gnd_node && n2 != gnd_node) &&
                     ((x1 == x2 && y1 != y2) || (x1 != x2 && y1 == y2));
    bool is_load = is_current && n2 == gnd_node;
    bool is_z_res = is_res && (net_id1 == net_id2) &&
                    (n1 != gnd_node && n2 != gnd_node) &&
                    (x1 == x2 && y1 == y2);
    if (is_xy_res) {
      grid_desc.wires.emplace_back(x1, y1, x2, y2, v);
    } else if (is_load) {
      grid_desc.loads.emplace_back(x1, y1, v);
    } else if (is_z_res) {
      grid_desc.pads.emplace_back(x1, y1, v);
    }
  }
}
