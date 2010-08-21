# Start Header ------------------------------------------------------------
#
#    File Name: disttree.py
#
#    Revision : 1.02
#
#    Purpose  : copy files to a distribution tree
#
#    Language : Python
#
#    Platform : Windows NT/MAC etc
#
#    Author       Date        Comments
#    ------------------------------------------------------------------------
#    UHoffmann    25Jan2000   added -f option
#    UHoffmann    25Jan2000   added -D option
#    UHoffmann    10Jan2000   added -w option
#    UHoffmann    10Jan2000   added -n option
#    UHoffmann    06Jan2000   initial version
#
# - End Header --------------------------------------------------------------

import os, sys, shutil, getopt, re

verbose=0
lino=0
simulation=0
filesMustExist=0
force=0

assignement=re.compile("[ \t]*([_a-zA-Z][_a-zA-Z0-9]*)[ \t]*=(.*)$")

def error(message):
    if lino==0:
        print "%s: %s on command line!" % (os.path.basename(sys.argv[0]),
                                           message)
    else:
        print "%s: %s in line %d!" % (os.path.basename(sys.argv[0]),
                                      message,lino)

def copy(src,destdir):
    if os.path.isdir(src):
        for file in os.listdir(src):
            if os.path.isdir(src+os.sep+file):
                # destdir+os.sep+file denotes a destination directory
                if not os.path.isdir(destdir+os.sep+file):
                    try:
                        if not simulation:
                            os.makedirs(destdir+os.sep+file)
                    except OSError,msg:
                        error("Cannot create directory %s (%s)" % (destdir,msg))
                        sys.exit(8)
                copy(src+os.sep+file,destdir+os.sep+file)
            else:
                copy(src+os.sep+file,destdir)

    elif os.path.isfile(src):
        try:
            if not simulation:
                try:
                    shutil.copy2(src,destdir)
                except:
                    destfile=destdir+os.sep+os.path.basename(src)
                    if force and os.path.exists(destfile):
                        os.chmod(destfile,0777)
                        os.remove(destfile)
                        shutil.copy2(src,destdir)
                    else:
                        type,value=sys.exc_info()[:2]
                        raise type, value
        except IOError, msg:
            if verbose:
                print "%-40s -|-> %s" % (src,destdir),
            error("Copy failed for file %s (%s)" % (src,msg))
            sys.exit(3)

        if verbose:
            print "%-40s ---> %s" % (src,destdir)

    else:
        # src no dir nor file
        error("File '%s' not found" % (src,))
        if filesMustExist:
            sys.exit(6)

def dictlookup(dict,matchobj):
    match=matchobj.group(0)
    pre=match[0]  # the non $
    key=match[2:] # cut the non $ and the $
    #print "-->",key
    #if dict.has_key(key):
    #    return pre+dict[key]
    #else:
    #    return match
    try:
        return pre+dict[key]
    except:
        error("Undeclared variable %s" % (key,))
        sys.exit(2)

def subst(str,dict):
    # substitute all occurences of variables of the form $var
    # by their values in string
    # e.g. "hello $$ $person",{"person": "you"} -> "hello $ you"
    # $$ will be replaced by $
    #print "subst('%s',%s)" %(str,dict)
    repl=lambda key,dict=dict: dictlookup(dict,key)

    ident=re.compile("[^\\$]\\$[_a-zA-Z][_a-zA-Z0-9]*")

    str=re.sub(ident,repl," "+str)[1:] # add leading space for pattern

    return re.sub("\\$\\$","$",str)


def disttree(specfilename, variables={}):
    comment=re.compile("[ \t]*#.*$")
    global assignement
    destdirspec=re.compile("[ \t]*\[(.*)\]")

    destdir=""
    global lino
    lino=0

    for line in open(specfilename,"r").readlines():
        lino=lino+1
        line=line[:-1]
        line=re.sub("[ \t]*$","",line)
        line=re.sub("^[ \t]*","",line)
        if line=="":
            continue
        # print "'%s'" % (line,)
        line=re.sub(comment,"",line)

        if line=="":
            continue

        m=assignement.match(line)
        if m:
            var=m.group(1)
            expr=subst(m.group(2),variables)
            variables[var] = subst(expr,variables)
            continue

        m=destdirspec.match(line)
        if m:
            destdir=subst(m.group(1),variables)
            continue

        src=subst(line, variables)
        if destdir=="":
            error("No destination directory specified")
            sys.exit(4)

        if not os.path.isdir(destdir):
            try:
                if not simulation:
                    os.makedirs(destdir)
            except OSError,msg:
                error("Cannot create directory %s (%s)" % (destdir,msg))
                sys.exit(5)

        copy(src,destdir)


def usage():
    name = os.path.basename(sys.argv[0])
    print "Distribution Tree Creator"
    print "Create a distribution tree according to disttreespec"
    print
    print "Usage: python %s [options] disttreespec" % (name,)
    print "       options:"
    print "          -v             verbose"
    print "          -n             don't actually perform copy"
    print "          -w             just warn if a file does not exist"
    print "          -f             force (overwrite existing r/o files)"
    print "          -D name=value  preset variable"
    print
    print "Example: python %s -v -D DST=X:\ distribution.spec" % (name,)
    sys.exit(99)

def main(argv):
    if len(argv)<2: usage()
    try:
        optlist, argv = getopt.getopt(argv[1:], "D:fnvw")
    except getopt.error,msg:
        print msg
        usage()
        sys.exit(9)

    # the global variables for options
    global verbose; verbose=0
    global simulation; simulation=0
    global filesMustExist; filesMustExist=1
    global force; force=0

    variables={} # predefined variables

    for opt,val in optlist:
        if opt=="-v":
            verbose=1
        elif opt=="-n":
            simulation=1
        elif opt=="-w":
            filesMustExist=0
        elif opt=="-f":
            force=1
        elif opt=="-D":
            global assignement
            m=assignement.match(val)
            if m:
                var=m.group(1)
                expr=subst(m.group(2),variables)
                variables[var] = subst(expr,variables)
            else:
                error("Illegal parameter '%s' to -D option" % (val,))
                usage()
        else:
            error("Unknown option: %s" % (opt,))
            usage()

    if len(argv)!=1:
        usage()

    disttreespec=argv[0]

    # do it
    disttree(disttreespec,variables)

    return 0


if __name__=="__main__":
    try:
        rc=main(sys.argv)
    except KeyboardInterrupt:
        error("User aborted")
        sys.exit(10)
    sys.exit(rc)

