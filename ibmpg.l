%option noyywrap

%{

#include <cctype>
#include "ibmpg_parser.hpp"

double parseValue(const char *str);

%}

ALPHA    [_A-Za-z]
DIGIT    [0-9]
ALPHANUM [_A-Za-z0-9]
STRING   {ALPHANUM}+
INTEGER  {DIGIT}+
REAL     [\-\+]?([0-9]*\.?[0-9]+|[0-9]+\.)([Ee](\+|\-)?[0-9]+)?

EOL         \n
BLANK       [ \t\r]+
S_UNIT      [Ff]|[Pp]|[Nn]|[Uu]|[Mm]|[Kk]|[Mm]|[Xx]|[Gg]|[Tt]|[Mm][Ee][Gg]
VALUE       ({REAL}|[\-]?{INTEGER}){S_UNIT}
COMMENTLINE \*.*\n

P_RESISTOR [r|R]{STRING}
P_VSOURCE  [v|V]{STRING}
P_ISOURCE  [i|I]{STRING}

CMD_OP  \.[Oo][Pp]
CMD_END \.[Ee][Nn][Dd]

%%

{INTEGER} { yylval.num = atoi(yytext); return INTEGER; }
{REAL}    { yylval.value = atof(yytext); return REAL; }
{VALUE}   { yylval.value = parseValue(yytext); return REAL; }

{EOL}         { return EOL; }
{COMMENTLINE} { yylval.str = strdup(yytext); return COMMENTLINE; }

{P_RESISTOR} { yylval.str = strdup(yytext); return P_RESISTOR; }
{P_VSOURCE}  { yylval.str = strdup(yytext); return P_VSOURCE; }
{P_ISOURCE}  { yylval.str = strdup(yytext); return P_ISOURCE; }

{CMD_OP}  { return CMD_OP; }
{CMD_END} { return CMD_END; }

{STRING} { yylval.str = strdup(yytext);  return STRING; }
{BLANK}  {}
.        { return YYerror; }

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
