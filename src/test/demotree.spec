# demo distribution tree

# A distribution tree specification has three syntaxtic elements:
#
# a) variable definitions of the form
#              variable = path
#
# b) specifications of target directories in the form
#    [path]
#
# c) specification of source files in the form
#    path
#    if path denotes a directory its files are recursively copied
#
# path may have references to variables by the $variable syntax

OK=false

%if $TESTVAR==
%print TESTVAR ist leer
OK=true
%else
%print TESTVAR ist nicht leer sondern hat den Wert '$TESTVAR'
%endif

%if $TESTVAR==one
%print TESTVAR ist 'one'
OK=true
%else
%print TESTVAR hat nicht den Wert 'one' sondern '$TESTVAR'
%endif

%if $OK==true
%print TESTVAR ist leer oder hat den Wert 'one'
%error done
%else
%print TESTVAR ist nicht leer und auch nicht 'one' sondern '$TESTVAR'
%endif


#%print $PATH
# Example
DST=tmp
SRC=src
TST=$SRC/test

[$DST/disttree]
$SRC/disttree.py
$TST/demotree.spec
@ rm -f newname; mv disttree.py newname; chmod 444 newname

$SRC/*.xlerb

"$TST/demotree.spec"
"$TST/@xlerb"

# Do wildcards work? Not in version 1.06
"$TST/*tree.spec"
$TST/*tree.spec

[$DST/disttree/subdir]
$TST/subdir
