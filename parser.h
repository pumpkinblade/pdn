#ifndef __PARSER_H__
#define __PARSER_H__

#include "circuit.h"

struct SpiceCircuit : Circuit {
  lemon::CrossRefMap<GraphT, GraphT::Node, std::string> nodeNameMap;
  GraphT::ArcMap<std::string> arcCompNameMap;

  SpiceCircuit() : Circuit(), nodeNameMap(graph), arcCompNameMap(graph) {
    nodeNameMap.set(graph.nodeFromId(0), "0");
  }
};

class SpiceParser {
public:
  SpiceParser(const std::string &file);

  void run();

  std::shared_ptr<SpiceCircuit> circuit() const { return m_ckt; }

private:
  std::string m_file;
  std::shared_ptr<SpiceCircuit> m_ckt;
};

#endif
