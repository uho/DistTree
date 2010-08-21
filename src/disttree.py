# Start Header ------------------------------------------------------------
#
#    File Name: disttree.py
#
#    Revision : 1.10
#
#    Purpose  : copy files to a distribution tree
#
#    Language : Python
#
#    Platform : Windows NT/MAC etc
#
#    Author       Date        Comments
#    ------------------------------------------------------------------------
#    UHoffmann    01Jun2005   Optionally initialize variables from environment
#    UHoffmann    29Oct2004   Added Wildcard handling
#    UHoffmann    29Oct2004   Improved error handling in copy
#    UHoffmann    23Mar2004   Added %if $VAR==val
#    UHoffmann    15May2002   Added %for and %end-for w/ synchronous vars
#    UHoffmann    14May2002   fixed double eval bug in assignement and -D hdler
#    UHoffmann    14May2002   Added $(VAR) variable notation
#    UHoffmann    14May2002   Added empty %print statement
#    UHoffmann    26Jun2001   Fixed formatting bug in md5
#    UHoffmann    25Jun2001   Added logfile and manifest (md5) support
#    UHoffmann    22Feb2001   Added support for retry and include
#    UHoffmann    01Sep2000   fixed directory handling in command execution
#    UHoffmann    23Aug2000   conditional processing
#    UHoffmann    22Aug2000   fixed end of file problem
#    UHoffmann    16Mar2000   added execution of batch commands
#    UHoffmann    09Mar2000   added -c option
#    UHoffmann    09Mar2000   added -a option
#    UHoffmann    25Jan2000   added -f option
#    UHoffmann    25Jan2000   added -D option
#    UHoffmann    10Jan2000   added -w option
#    UHoffmann    10Jan2000   added -n option
#    UHoffmann    06Jan2000   initial version
#
# - End Header --------------------------------------------------------------

# This file specifies the distribution tree of the a software system.
# It determines the directory structure and the files tha
# will be found in the target version of that software.
# It is used to copy files resulting from the build process.
#
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
#
# Conditional processing is expressed by the directives %ifdef, %ifndef,
# %else, %endif; output by %print resp. %error (aborts processing)
#

import os, sys, shutil, getopt, re, string, glob

# Regular expression for different kinds of lines
ASSIGNEMENT=re.compile("[ \t]*([_a-zA-Z][_a-zA-Z0-9]*)[ \t]*=(.*)$")
DESTDIRSPEC=re.compile("[ \t]*\[(.*)\]")
COMMENT=re.compile("[ \t]*#.*$")
QUOTED=re.compile('[ \t]*"(.*)"')
COMMAND=re.compile("[ \t]*@[ \t]*(.*)")

DIRECTIVE=re.compile("[ \t]*(%[^ ]*)")
IFEQUAL_DIRECTIVE=re.compile(
    "[ \t]*%if[ \t]*(\$[_a-zA-Z][_a-zA-Z0-9]*)[ \t]*==(.*)$")
IFDEF_DIRECTIVE=re.compile("[ \t]*%ifdef[ \t]*([_a-zA-Z][_a-zA-Z0-9]*)")
IFNDEF_DIRECTIVE=re.compile("[ \t]*%ifndef[ \t]*([_a-zA-Z][_a-zA-Z0-9]*)")
ELSE_DIRECTIVE=re.compile("[ \t]*%else")
ENDIF_DIRECTIVE=re.compile("[ \t]*%endif")
PRINT_DIRECTIVE=re.compile("[ \t]*%print( (.*)|$)")
ERROR_DIRECTIVE=re.compile("[ \t]*%error (.*)")
INCLUDE_DIRECTIVE=re.compile("[ \t]*%include (.*)")
FOR_DIRECTIVE=re.compile(
    "[ \t]*%for[ \t]*([_a-zA-Z][_a-zA-Z0-9]*(,[_a-zA-Z][_a-zA-Z0-9]*)*)[ \t]*"
    "(delimiter '(.)')?[ \t]*"
    "in (.*)$")
ENDFOR_DIRECTIVE=re.compile("[ \t]*%endfor")

# States for conditional processing
PROCESSING="Processing"
NOPROCESSING="NoProcessing"
SKIP="skip"


def error(message):
    # where is a pair (line, file) that identifies the current read location
    try:
        line,file=where
    except:
        line,file=(0,"")

    if file=="":
        msg="%s: %s on command line!" % (os.path.basename(sys.argv[0]),
                                         message)
    else:
        msg="%s: %s in file %s line %d!" % (os.path.basename(sys.argv[0]),
                                            message,file,line)
    print msg

def askRetryQuestion():
    a='e'
    while a not in ['','r','R','a','A']:
        print "R)etry operation or A)bort? [R/a]"
        a=raw_input()
    return a in ['r','R','']

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
        retry=1
        while retry:
            retry=0
            try:
                destfile=destdir+os.sep+os.path.basename(src)
                if not simulation:
                    try:
                        shutil.copy2(src,destdir)
                    except:
                        if force and os.path.exists(destfile):
                            os.chmod(destfile,0777)
                            os.remove(destfile)
                            shutil.copy2(src,destdir)
                        else:
                            type,value=sys.exc_info()[:2]
                            raise type, value
                    if resetAttributes:
                        os.chmod(destfile,0666)
            except EnvironmentError, msg:
                if verbose:
                    print "%-40s -|-> %s" % (src,destdir),
                error("Copy failed for file '%s' (%s)" % (src,msg))
                if retryQuestion:
                    retry=askRetryQuestion()
                if not retry:
                    sys.exit(3)

        if verbose:
            print "%-40s ---> %s" % (src,destdir)

        if logfile:
            if simulation:
                logfile.write("Simulation: ")
            if md5sums:
                logfile.write("%s *" % (md5digest(src),))
            logfile.write("%s\n" % (destfile,))

    else:
        # src no dir nor file
        error("File '%s' not found" % (src,))
        if filesMustExist:
            sys.exit(6)

def md5digest(filename):
    # Calculate an MD5 hash for the file with name filename (binary mode)
    import md5
    import string
    m=md5.new()
    f=open(filename,"rb")
    if f:
        try:
            while 1:
                buf=f.read(10000000)
                if buf=='':
                    break
                m.update(buf)
        except:
            digest='\000'*16
    else:
        digest='\000'*16
    return string.join(map(lambda byte:'%02x' % (ord(byte),), m.digest()),'')

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
        # simple VAR form
        return pre+dict[key]
    except:
        # extended $(VAR) form
        if key[0]=='(' and key[-1]==')':
            key=key[1:-1]
            try:
                return pre+dict[key]
            except:
                pass

    error("Undeclared variable '%s'" % (key,))
    sys.exit(2)

def subst(str,dict):
    # substitute all occurences of variables of the form $var
    # by their values in string
    # e.g. "hello $$ $person",{"person": "you"} -> "hello $ you"
    # $$ will be replaced by $
    #print "subst('%s',%s)" %(str,dict)
    repl=lambda key,dict=dict: dictlookup(dict,key)

    ident=re.compile("[^\\$]\\$"                     # a single $
                     "([_a-zA-Z][_a-zA-Z0-9]*|"      # followed by  VAR
                     "\([_a-zA-Z][_a-zA-Z0-9]*\))")  # or (VAR)

    str=re.sub(ident,repl," "+str)[1:] # add leading space for pattern

    return re.sub("\\$\\$","$",str)


def makedir(dir):
    if not simulation:
        try:
            os.makedirs(dir)
        except OSError,msg:
            error("Cannot create directory %s (%s)" % (dir,msg))
            sys.exit(5)


def processing(conditionals):
    return (conditionals==[] # outside all conditionals
            or (conditionals[0] is PROCESSING))

def disttree(specfilename, variables={}):

    destdir=""
    lino=0
    conditionals=[]  # stack to represent conditional tree structure
    loopdata=[] # stack of looping information

    lines=open(specfilename,"r").readlines()
    while lino<len(lines):
        line=lines[lino]
        lino=lino+1

        global where
        where=(lino, specfilename)

        if line[-1]=='\n':
            line=line[:-1]
        line=re.sub("[ \t]*$","",line)
        line=re.sub("^[ \t]*","",line)
        if line=="":
            continue

        # print "Processing line %s: '%s'" % (lino,line)

        line=re.sub(COMMENT,"",line)

        if line=="":
            continue

        # print line, conditionals, processing(conditionals)

        # conditional processing directive?
        m=IFDEF_DIRECTIVE.match(line)
        if m:
            if processing(conditionals):
                var=m.group(1)
                if variables.has_key(var):
                    conditionals=[PROCESSING]+conditionals
                else:
                    conditionals=[NOPROCESSING]+conditionals
            else:
                conditionals=[SKIP]+conditionals
            continue

        m=IFEQUAL_DIRECTIVE.match(line)
        if m:
            if processing(conditionals):
                var=m.group(1)
                val=m.group(2)
                if subst(var, variables)==subst(val,variables):
                    conditionals=[PROCESSING]+conditionals
                else:
                    conditionals=[NOPROCESSING]+conditionals
            else:
                conditionals=[SKIP]+conditionals
            continue

        m=IFNDEF_DIRECTIVE.match(line)
        if m:
            if processing(conditionals):
                var=m.group(1)
                if variables.has_key(var):
                    conditionals=[NOPROCESSING]+conditionals
                else:
                    conditionals=[PROCESSING]+conditionals
            else:
                conditionals=[SKIP]+conditionals
            continue

        m=ELSE_DIRECTIVE.match(line)
        if m:
            if conditionals:
                if conditionals[0] is PROCESSING:
                    conditionals[0]=NOPROCESSING
                elif conditionals[0] is NOPROCESSING:
                    conditionals[0]=PROCESSING
                # SKIP remains unchanged
            else:
                error("'%else' directive encountered out of context")
                sys.exit(6)
            continue

        m=ENDIF_DIRECTIVE.match(line)
        if m:
            if conditionals:
                conditionals=conditionals[1:]
            else:
                error("'%endif' directive encountered out of context")
                sys.exit(6)
            continue

        # non conditional directive: do conditional processing

        if not processing(conditionals):
            continue

        m=FOR_DIRECTIVE.match(line)
        if m:
            vars=string.split(m.group(1),',')
            expr=m.group(5)
            delimiter=','
            if m.group(3):
                delimiter=m.group(4)

            # evaluate list expression once
            sequence=string.split(subst(expr,variables),delimiter)
            if sequence==[]:
                error("'%for' directive with empty sequence")
                sys.exit(11)
            if (len(sequence) % len(vars))!=0:
                error("number of variables does not match sequence length")
                sys.exit(12)

            for var in vars:
                variables[var]=sequence[0]  # already evaluated
                sequence=sequence[1:]

            loopdata=[(vars, sequence, lino)]+loopdata
            continue

        m=ENDFOR_DIRECTIVE.match(line)
        if m:
            if loopdata:
                (vars,sequence,startlino)=loopdata[0]
                if sequence==[]:
                    # iteration done
                    loopdata=loopdata[1:]
                else:
                    # another iteration
                    for var in vars:
                        variables[var]=sequence[0] # already evaluated
                        sequence=sequence[1:]
                    loopdata[0]=(vars,sequence,startlino)
                    lino=startlino
            else:
                error("'%endfor' directive encountered out of context")
                sys.exit(6)
            continue

        m=PRINT_DIRECTIVE.match(line)
        if m:
            msg=''
            if m.group(1):
                msg=subst(m.group(2),variables)
            print msg
            continue

        m=ERROR_DIRECTIVE.match(line)
        if m:
            msg=subst(m.group(1),variables)
            error(msg)
            sys.exit(7)

        m=INCLUDE_DIRECTIVE.match(line)
        if m:
            newSpecfilename=subst(m.group(1),variables)
            disttree(newSpecfilename, variables)
            continue

        m=DIRECTIVE.match(line)
        if m:
            directive=m.group(1)
            error("unknown directive '%s' encountered" % (directive,))
            sys.exit(6)

        # non directives

        m=ASSIGNEMENT.match(line)
        if m:
            var=m.group(1)
            expr=m.group(2)
            variables[var] = subst(expr,variables)
            continue

        m=DESTDIRSPEC.match(line)
        if m:
            destdir=subst(m.group(1),variables)
            if createEmptyDirectories and not os.path.isdir(destdir):
                makedir(destdir)
            continue

        m=COMMAND.match(line)
        if m:
            cmd=subst(m.group(1),variables)
            if verbose:
                print "Executing '%s'" % (cmd,)
            try:
                if not simulation:
                    current=os.getcwd()
                    try:
                      os.chdir(destdir)
                      if os.system(cmd):
                          error("'%s' failed" % (cmd,))
                    finally:
                       os.chdir(current)
            finally:
                pass
            continue


        # none of that above: assume file to copy

        # remove surrounding quotes, if any
        quoted=QUOTED.match(line)
        if quoted:
            line=quoted.group(1)

        src=subst(line, variables)

        if destdir=="":
            error("No destination directory specified")
            sys.exit(4)

        if not os.path.isdir(destdir):
            makedir(destdir)

        if quoted:
            copy(src,destdir)
        else:
            pathnames=glob.glob(src)
            if len(pathnames)==0:
                error("No files matching '%s' found" % (src,))
                if filesMustExist:
                    sys.exit(6)
            else:
                for pathname in pathnames:
                    copy(pathname, destdir)

    if conditionals:
        error("'%endif' directive missing")

    if loopdata:
        error("'%endfor' directive missing")


def usage():
    name = os.path.basename(sys.argv[0])
    print "Distribution Tree Creator"
    print "Create a distribution tree according to disttreespec"
    print
    print "Usage: python %s [options] disttreespec" % (name,)
    print "       options:"
    print "          -v             verbose"
    print "          -q             on copy error, ask retry question"
    print "          -n             don't actually perform copy"
    print "          -w             just warn if a file does not exist"
    print "          -f             force (overwrite existing r/o files)"
    print "          -a             reset read-only attributes"
    print "          -c             don't create empty directories"
    print "          -m             generate md5sums in logfile"
    print "          -e             initialize variables from environment"
    print "          -l logfile     write log file"
    print "          -D name=value  preset variable"
    print
    print "Example: python %s -v -D DST=X:\ distribution.spec" % (name,)
    sys.exit(99)

def main(argv):
    if len(argv)<2: usage()
    try:
        optlist, argv = getopt.getopt(argv[1:], "D:l:efnvwacmq")
    except getopt.error,msg:
        print msg
        usage()
        sys.exit(9)

    # the global variables for options
    global verbose; verbose=0
    global simulation; simulation=0
    global filesMustExist; filesMustExist=1
    global force; force=0
    global resetAttributes; resetAttributes=0
    global createEmptyDirectories; createEmptyDirectories=1
    global retryQuestion; retryQuestion=0
    global logfile; logfile=None
    global md5sums; md5sums=None

    variables={} # predefined variables

    if ('-e','') in optlist:
        # initialize variables from environment
        for envVar,envVal in os.environ.items():
            variables[envVar] = envVal

    for opt,val in optlist:
        if opt=="-v":
            verbose=1
        elif opt=="-n":
            simulation=1
        elif opt=="-w":
            filesMustExist=0
        elif opt=="-f":
            force=1
        elif opt=="-a":
            resetAttributes=1
        elif opt=="-c":
            createEmptyDirectories=0
        elif opt=="-q":
            retryQuestion=1
        elif opt=="-D":
            m=ASSIGNEMENT.match(val)
            if m:
                var=m.group(1)
                expr=m.group(2)
                variables[var] = subst(expr,variables)
            else:
                error("Illegal parameter '%s' to -D option" % (val,))
                usage()
        elif opt=="-l":
            try:
                logfile=open(val,"w")
            except:
                error("Cannot open logfile '%s'" % (val,))
                usage()
        elif opt=="-m":
            md5sums=1
        elif opt=="-e":
            pass # handled above
        else:
            error("Unknown option: %s" % (opt,))
            usage()

    if len(argv)!=1:
        usage()

    disttreespec=argv[0]

    if not os.path.exists(disttreespec):
        error("Specification '%s' does not exist" % (disttreespec,))
        usage()

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

