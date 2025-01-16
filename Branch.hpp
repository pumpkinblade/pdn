#pragma once

#include <string>

enum class BranchType { Unknown, Resistor, VSource, ISource };

class Branch {
public:
  Branch() = default;
  Branch(const std::string &name, double value);
  Branch(const std::string &name, BranchType type, double value);

  const std::string &name() const { return m_name; }
  double value() const { return m_value; }
  BranchType type() const { return m_type; }

private:
  std::string m_name;
  BranchType m_type;
  double m_value;
};
