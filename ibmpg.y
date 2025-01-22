%{

#include "IbmpgParser.hpp"
#include <regex>
#include <string>

extern IbmpgParser *pg;

int yylex(void);
void yyerror(const char *s);

%}

%token<str> CMD_OP CMD_END
%token<str> P_RESISTOR P_VSOURCE P_ISOURCE

%token<num> INTEGER
%token<str> EOL STRING COMMENTLINE
%token<value> REAL VALUE

%type<str> node
%type<value> value
%type<str> op end
%type<str> resistor isource vsource
%type<str> command component comment
%type<str> line lines

%union {
  char *str;
  int num;
  double value;
}

%%

lines
: lines line {}
| {}
;

line
: component EOL {}
| command EOL {}
| EOL {}
| comment {}
;

command
: op
| end
;

component
: resistor
| vsource
| isource
;

resistor
: P_RESISTOR node node value { pg->makeComponent($1, $2, $3, $4); }
;

vsource
: P_VSOURCE node node value { pg->makeComponent($1, $2, $3, $4); }
;

isource
: P_ISOURCE node node value { pg->makeComponent($1, $2, $3, $4); }
;

comment
: COMMENTLINE { pg->makeComment($1); }
;

op
: CMD_OP {}
;

end
: CMD_END {}
;

value
: REAL { $$ = $1; }
| INTEGER { $$ = $1; }
;

node
: STRING { $$ = $1; }
| INTEGER { $$ = (char *)malloc(32); sprintf($$, "%d", $1); }
;

%%

void yyerror(const char *s) {
    fprintf(stderr, "error: %s\n", s);
}
