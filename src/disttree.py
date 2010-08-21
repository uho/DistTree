# Start Header ------------------------------------------------------------
#
#    File Name: disttree.py
#
#    Revision : 1.01
#
#    Purpose  : copy files to a distribution tree
#
#    Language : Python
#
#    Platform : Windows NT/MAC etc
#
#    Author       Date        Comments
#    ------------------------------------------------------------------------
#    UHoffmann    10Jan2000   added -w option
#    UHoffmann    10Jan2000   added -n option
#    UHoffmann    06Jan2000   initial version
#
# - End Header --------------------------------------------------------------

import os, sys, shutil, time, getopt, glob, re

verbose=0
lino=0
simulation=0
filesMustExist=0

def error(message):
    print "%s: %s in line %d!" % (os.path.basename(sys.argv[0]),message,lino)

def copy(src,dest):
    if os.path.isdir(src):
        for file in os.listdir(src):
            if os.path.isdir(src+os.sep+file):
                if not os.path.isdir(dest+os.sep+file):
                    try:
                        if not simulation:
                            os.makedirs(dest+os.sep+file)
                    except OSError,msg:
                        error("Cannot create directory %s (%s)" % (destdir,msg))
                        sys.exit(8)
                copy(src+os.sep+file,dest+os.sep+file)
            else:
                copy(src+os.sep+file,dest)

    elif os.path.isfile(src):
        try:
            if not simulation:
                shutil.copy2(src,dest)
        except IOError, msg:
            if verbose:
                print "%-40s -|-> %s" % (src,dest),
            error("Copy failed for file %s (%s)" % (src,msg))
            sys.exit(3)

        if verbose:
            print "%-40s ---> %s" % (src,dest)

    else:
        # no dir nor file
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


def disttree(specfilename):
    comment=re.compile("[ \t]*#.*$")
    assignement=re.compile("[ \t]*([_a-zA-Z][_a-zA-Z0-9]*)[ \t]*=(.*)$")
    destdirspec=re.compile("[ \t]*\[(.*)\]")

    variables={}
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
    print "Distribution Tree Creator"
    print "Create a distribution tree according to disttreespec"
    print
    print ("Usage: python %s [options] disttreespec" %
           (os.path.basename(sys.argv[0]),))
    print "       options:"
    print "          -v verbose"
    print "          -n don't actually perform copy"
    print "          -w just warn if a file does not exist"
    sys.exit(99)

def main(argv):
    if len(argv)<2: usage()
    try:
        optlist, argv = getopt.getopt(argv[1:], "vwn")
    except getopt.error,msg:
        print msg
        usage()
        sys.exit(9)

    # the global variables for options
    global verbose; verbose=0
    global simulation; simulation=0
    global filesMustExist; filesMustExist=1

    for opt,val in optlist:
        if opt=="-v":
            verbose=1
        elif opt=="-n":
            simulation=1
        elif opt=="-w":
            filesMustExist=0
        else:
            error("Unknown option: %s" % (opt,))
            usage()

    if len(argv)!=1:
        usage()

    disttreespec=argv[0]

    # do it
    disttree(disttreespec)

    return 0


if __name__=="__main__":
    try:
        rc=main(sys.argv)
    except KeyboardInterrupt:
        error("User aborted")
        sys.exit(10)
    sys.exit(rc)

