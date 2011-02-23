import os
import sys
import shutil
import subprocess
import urllib2
import getopt

MODULE = 'spocktests'

COMMANDS = ['spocktests:clean', 'spocktests:run']

HELP = {
    'spocktests:run': 'Assert SPOCK specifications under test/ againt running test server. Use --specfilter=Data* to filter spec class name',
    'spocktests:clean': 'Clean any test related class files',
}

def execute(**kargs):
    command = kargs.get("command")
    app = kargs.get("app")
    args = kargs.get("args")
    env = kargs.get("env")

    app.check()

    if command == "spocktests:clean":
        clean_tests(app)
    elif command == "spocktests:run":
        compile_run_tests(app, env, args)
    else:
        assert False, "Unknown command %s" % command

def clean_tests(app):
    if os.path.exists(os.path.join(app.path, 'tmp')):
        shutil.rmtree(os.path.join(app.path, 'tmp'))
        #this also removed groovytests sub directories
    if os.path.exists(os.path.join(app.path, 'precompiled')):
        shutil.rmtree(os.path.join(app.path, 'precompiled'))     

def compile_run_tests(app, env, args):
    spec_filter = '*'
    try:
        optlist, args = getopt.getopt(args, '', ['specfilter='])
        for o, a in optlist:
            if o in ('--specfilter'):
                spec_filter = a
    except getopt.GetoptError, err:
        print "~ %s" % str(err)
        print "~ Sorry, unrecognized option"
        print "~ "
        sys.exit(-1)

    print '~ Checking a test server is running...'
    http_port = app.readConf('http.port')
    try:
        proxy_handler = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_handler)
        status = opener.open('http://localhost:%s/@status' % http_port)
        print "~ ...ok, got status %s" % status # NOT REACHED
    except Exception, e:
        if hasattr(e, 'code') and e.code in [401, 503]:
            # normal - status not started or needs auth key, but now we know the server is alive
            print "~ ...ok."
        else:
            print "~ Ops! %s" % e
            print "~ Cannot reach http://localhost:%s, make sure 'play test' is running" % http_port
            print
            sys.exit(2)
    
    print '~ Finding resources... %s' % args
    build_file = None
    for m in app.modules(): 
        if 'spock' in m and 'tests' in m:
            build_file = os.path.join(m, 'runtests.xml')
    if not build_file:
        print "Could not find runtests.xml, check how modules are setup (%s)" % app.modules()
        sys.exit(1)
    
    print "~"
    print "~ Compiling..."
    print "~"
    app.check()
    java_cmd = app.java_cmd(args)
    java_cmd.insert(2, '-Dprecompile=yes')
    try:
        subprocess.call(java_cmd, env=os.environ)
    except OSError:
        print "Could not execute the java executable, please make sure the JAVA_HOME environment variable is set properly (the java executable should reside at JAVA_HOME/bin/java). "
        sys.exit(-1)
    compiledClasspath = [os.path.join(app.path, 'precompiled', 'java'),
                         os.path.join(app.path, 'tmp', 'classes')]
    print
    
    
    print "~"
    print "~ Running tests..."
    print "~"
    cp = ":".join(app.getClasspath() + compiledClasspath)
    cmd = 'ant -f %s -Dplay.path=%s -Dapp.path=%s -Dapp.classpath=%s -Dspec.filter=%s' % (build_file, env["basedir"], app.path, cp, spec_filter)
    #print "~ (with '%s')" % cmd
    try:
        os.system(cmd)
    except OSError:
        print "Error executing ant, please make sure it is available on path."
        sys.exit(-1)
    print "~"
    if os.path.exists(os.path.join(app.path, 'tmp', 'spocktests', 'result.failed')):
        print "~ ...failed"
        sys.exit(42)

