#include "IbmpgCircuit.hpp"
#include <fmt/core.h>
#include <regex>

IbmpgCircuit *g_ckt = nullptr;
void yyset_in(FILE *);
int yyparse(void);
int yylex_destroy(void);

void IbmpgCircuit::readNetlist(const std::string &file_path) {
  FILE *file = fopen(file_path.c_str(), "r");
  if (file == NULL) {
    fmt::println("unable to open spice file {}", file_path);
    return;
  }

  g_ckt = this;
  yyset_in(file);
  int ret = yyparse();
  fclose(file);
  yylex_destroy();
  g_ckt = nullptr;

  if (ret) {
    fmt::println("error occurred while parse spice netlist");
  }
}

void IbmpgCircuit::makeBranch(char *bran, char *node1, char *node2, double v) {
  auto n1 = ensureNode(node1);
  auto n2 = ensureNode(node2);
  connect(n1, n2, Branch(bran, v));
  free(bran);
  free(node1);
  free(node2);
}

void IbmpgCircuit::makeComment(char *comment) {
  std::regex pattern(
      R"(^\* layer: ([a-zA-Z0-9_]+),([a-zA-Z0-9_]+) net: ([0-9]+))");
  std::cmatch match;
  if (std::regex_search(comment, match, pattern)) {
    std::string layer_name = match[1].str();
    std::string net_name = match[2].str();
    int net_index = std::atoi(match[3].str().c_str());
    int net_type = (net_name == "GND") ? 0 : 1;
    m_layer_comments.emplace_back(net_index, net_type, layer_name);
  }
  free(comment);
}
