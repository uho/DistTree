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
%print TESTVAR is empty
OK=true
%else
%print TESTVAR is not empty but has value '$TESTVAR'
%endif

%if $TESTVAR==one
%print TESTVAR is 'one'
OK=true
%else
%print TESTVAR does not have the value 'one' but '$TESTVAR'
%endif

%if $OK==true
%print TESTVAR is empty or has value 'one'
%error done
%else
%print TESTVAR is not empty and neither has value 'one' but '$TESTVAR'
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

$TST/*xlerb

"$TST/demotree.spec"
"$TST/@xlerb"

# Do wildcards work? Use quote to have * in a name
"$TST/*tree.spec"
$TST/*tree.spec

[$DST/disttree/subdir]
$TST/subdir
