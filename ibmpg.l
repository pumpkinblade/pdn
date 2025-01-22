%option noyywrap nounput

%{

#include <cctype>
#include "ibmpg.tab.hpp"

double parseValue(const char *str);

%}

INTEGER [0-9]+
REAL    [\-\+]?([0-9]*\.?[0-9]+|[0-9]+\.)([Ee](\+|\-)?[0-9]+)?
S_UNIT  [Ff]|[Pp]|[Nn]|[Uu]|[Mm]|[Kk]|[Mm]|[Xx]|[Gg]|[Tt]|[Mm][Ee][Gg]
VALUE   ({REAL}|[\-]?{INTEGER}){S_UNIT}

%%

{INTEGER}+ { yylval.num = atoi(yytext); return INTEGER; }
{REAL}     { yylval.value = atof(yytext); return REAL; }
{VALUE}    { yylval.value = parseValue(yytext); return REAL; }

[rR][a-zA-Z0-9_]+ { yylval.str = strdup(yytext); return P_RESISTOR; }
[vV][a-zA-Z0-9_]+ { yylval.str = strdup(yytext); return P_VSOURCE; }
[iI][a-zA-Z0-9_]+ { yylval.str = strdup(yytext); return P_ISOURCE; }

\.[Oo][Pp]     { return CMD_OP; }
\.[Ee][Nn][Dd] { return CMD_END; }

[a-zA-Z_][a-zA-Z0-9_]* { yylval.str = strdup(yytext);  return STRING; }

\*.*\n  { yylval.str = strdup(yytext); return COMMENTLINE; }
\n      { return EOL; }
[ \t\r] {}
.       { return YYerror; }

%%

double parseValue(const char *str) {
  double value = atof(str);
  int len = strlen(str);
  if (std::tolower(str[len - 1]) == 'g')
    if (std::tolower(str[len - 2]) == 'e')
      if (std::tolower(str[len - 3]) == 'm')
        return value * 1e6;

  char u = str[len - 1];
  if (u == 'F' || u == 'f')
    value *= 1e-15;
  else if (u == 'P' || u == 'p')
    value *= 1e-12;
  else if (u == 'N' || u == 'n')
    value *= 1e-9;
  else if (u == 'U' || u == 'u')
    value *= 1e-6;
  else if (u == 'M' || u == 'm')
    value *= 1e-3;
  else if (u == 'K' || u == 'k')
    value *= 1e3;
  else if (u == 'X' || u == 'x')
    value *= 1e6;
  else if (u == 'G' || u == 'g')
    value *= 1e9;
  else if (u == 'T' || u == 't')
    value *= 1e12;

  return value; 
}
