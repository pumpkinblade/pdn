#include "Branch.hpp"
#include <cctype>

Branch::Branch(const std::string &name, double value)
    : m_name(name), m_type(BranchType::Unknown), m_value(value) {
  switch (std::tolower(m_name[0])) {
  case 'r':
    m_type = BranchType::Resistor;
    break;
  case 'v':
    m_type = BranchType::VSource;
    break;
  case 'i':
    m_type = BranchType::ISource;
    break;
  default:
    m_type = BranchType::Unknown;
    break;
  }
}

Branch::Branch(const std::string &name, BranchType type, double value)
    : m_name(name), m_type(type), m_value(value) {}
