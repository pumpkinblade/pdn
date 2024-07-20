#ifndef __CIRCUIT_H__
#define __CIRCUIT_H__

#include <lemon/maps.h>
#include <lemon/smart_graph.h>

enum class PassiveComponentType { V, I, R, L, C };

struct PassiveComponent {
  PassiveComponentType type;
  double value;
};

using GraphT = lemon::SmartDigraph;

struct Circuit {
  GraphT graph;
  GraphT::ArcMap<PassiveComponent> arcCompMap;

  Circuit() : graph(), arcCompMap(graph) {
    graph.addNode();
  }
};

#endif
