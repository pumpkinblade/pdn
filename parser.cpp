#include "parser.h"
#include "utils.h"
#include <cstring>
#include <fstream>

#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))

SpiceParser::SpiceParser(const std::string &file)
    : m_file(file), m_ckt(new SpiceCircuit) {}

void SpiceParser::run() {
  std::ifstream fin(m_file);
  ASSERT(fin.is_open(), "Open spice netlist file `%s` failed!", m_file.c_str());
  char line[1024], compName[256], uName[256], vName[256], valStr[256];
  struct CharTypePair {
    char c;
    PassiveComponentType type;
  } charTypeTable[] = {
      {'v', PassiveComponentType::V}, {'i', PassiveComponentType::I},
      {'r', PassiveComponentType::R}, {'l', PassiveComponentType::L},
      {'c', PassiveComponentType::C},
  };
  struct CharMagPair {
    char c;
    double mag;
  } charMagTable[] = {
      {'n', 1e-9}, {'u', 1e-6}, {'m', 1e-3}, {'k', 1e3}, {'M', 1e6}, {'g', 1e9},
  };
  const char *delimiters = " \n";
  while (fin.getline(line, 1024)) {
    int i;
    PassiveComponentType type;
    char *tk = std::strtok(line, delimiters);
    if (!tk)
      continue;
    for (i = 0; i < ARRAY_SIZE(charTypeTable); ++i) {
      if (tk[0] == charTypeTable[i].c) {
        type = charTypeTable[i].type;
        break;
      }
    }
    if (i == ARRAY_SIZE(charTypeTable)) // not passive componenet, skipping
      continue;
    std::strcpy(compName, tk);                             // componenet name
    std::strcpy(uName, std::strtok(nullptr, delimiters));  // source node name
    std::strcpy(vName, std::strtok(nullptr, delimiters));  // target node name
    std::strcpy(valStr, std::strtok(nullptr, delimiters)); // value in string
    double value = std::strtod(valStr, &tk);
    for (auto [c, mag] : charMagTable) {
      if (c == tk[0]) {
        value *= mag;
        break;
      }
    }

    // now we have component of `type` with `value`
    // connecting `uName` and `vName`
    if (m_ckt->nodeNameMap.count(uName) == 0) {
      auto u = m_ckt->graph.addNode();
      m_ckt->nodeNameMap.set(u, uName);
    }
    if (m_ckt->nodeNameMap.count(vName) == 0) {
      auto v = m_ckt->graph.addNode();
      m_ckt->nodeNameMap.set(v, vName);
    }
    auto u = m_ckt->nodeNameMap(uName);
    auto v = m_ckt->nodeNameMap(vName);
    auto a = m_ckt->graph.addArc(u, v);
    m_ckt->arcCompMap.set(a, {type, value});
    m_ckt->arcCompNameMap.set(a, compName);
  }
}
