#=======================================================================================================
# Add functions and features for generating and running python extension unit tests.
#
import sys,os,venv,shutil
from waflib import TaskGen,Node,Task,Utils,Logs
from waflib.TaskGen import feature
# from waflib import Options

import lib_unit_tests

debug_python_venv = False
debug_python_venv_symlinks = False
debug_pyvenv_colour = "PINK"

class no_lib64_symlink_EnvBuilder(venv.EnvBuilder):
   """
   Override the EnvBuilder code that does a symlink to avoid problems with remote filesystems (see the use in _____ below).
   """

   def __init__(self,*args,**kwargs):
      super().__init__(*args,**kwargs)

   def ensure_directories(self,env_dir):
      # 1. Create the lib64 directory first, which stops the super().ensure_directories() from creating it as a symlink
      lib64_path = os.path.join(env_dir,"lib64")
      if not os.path.exists(lib64_path):
         os.makedirs(lib64_path)
      # 2. Use super().ensure_directories(env_dir) to do the rest of the work.
      context = super().ensure_directories(env_dir)
      # 3. Copy everything below lib to lib64.
      shutil.copytree(os.path.join(env_dir,"lib"),lib64_path,dirs_exist_ok=True)
      # return the super's return value
      return context

class ensure_python_venv(Task.Task):
   color = "BLUE"
   # after = ["vnum"]
   vars = []
   def __str__(self):
      tgen = self.generator # The TaskGen that created this task.
      bld = getattr(tgen,"bld",None) # The Build that created tgen.
      if None == bld:
         # The standard way to create a TaskGen is by calling Build.__call__() which sets the "bld" attribute.
         # If there is no "bld" attribute there is no telling how this was created or what is supposed to be run, so bail.
         return "non-standard python venv Task"
      if "VENV_PATH" in bld.env:
         # VENV_PATH is absolute, return the relative version.
         return bld.bldnode.find_or_declare(bld.env.VENV_PATH).path_from(bld.srcnode)
      return "Unknown"
   def keyword(self):
      # The VENV_SYMLINKS_WORK test isn't done until after run(), so we can't use it here :(.
      # tgen = self.generator # The TaskGen that created this task.
      # bld = getattr(tgen,"bld",None) # The Build that created tgen.
      # if None != bld and "VENV_SYMLINKS_WORK" in bld.env and not bld.env.VENV_SYMLINKS_WORK:
      #    return "Creating symlink-free python venv"
      return "Creating python venv"
   def run(self):
      if debug_python_venv or debug_python_venv_symlinks:
         Logs.pprint(debug_pyvenv_colour,"ensure_python_venv>>run() entered")
      tgen = self.generator # The TaskGen that created this task.
      bld = getattr(tgen,"bld",None) # The Build that created tgen.
      if None == bld:
         # The standard way to create a TaskGen is by calling Build.__call__() which sets the "bld" attribute.
         # If there is no "bld" attribute there is no telling how this was created or what is supposed to be run, so bail.
         Logs.pprint("RED","ensure_python_venv>>run() - no BuildContext, bailing")
         return -1
      bld_env = bld.env
      # Fetch the path to the venv we want.
      venv_path = bld_env.VENV_PATH if "VENV_PATH" in bld_env else None
      # Test for existence of the python executable in the venv to see if the venv is already present.
      python_exec_path = os.path.join(venv_path,"bin","python")
      if not os.path.exists(python_exec_path):
         # We need to create the virtual env.
         if "VENV_SYMLINKS_WORK" in bld.env:
            symlinks_work = bld_env["VENV_SYMLINKS_WORK"]
            use_lib64 = bld_env["VENV_USE_LIB64"]
            if debug_python_venv or debug_python_venv_symlinks:
               msg = "ensure_python_venv>>run(symlinks={!s}): Creating ordinary python venv in {:s}"
               Logs.pprint(debug_pyvenv_colour,msg.format(symlinks_work,venv_path))
         else:
            # Test for 64-bit lib needed (but only on some platforms)
            symlinks_work = True
            use_lib64 = False
            if debug_python_venv or debug_python_venv_symlinks:
               Logs.pprint(debug_pyvenv_colour,"ensure_python_venv>>run(): assume.symlinks={!s}".format(symlinks_work))
            if sys.maxsize > 2**32 and "windows" != bld_env.PLATSYS:
               # The built in venv.EnvBuilder code will put in a symlink lib64 -> lib on posix-like
               # systems because many distros do it and it's too complicated for python to try and
               # untangle it.  Unfortunately, if we want to run this build over any kind of remote
               # filesyste (e.g. NFS, SMB, VM shared folder, etc.) symlinks are not going to work.
               # Try making a symlink to a directory to see if we need to fiddle things.
               # The symlink issue isn't variant dependent, but put the results into the variant env anyways.
               lib64_path = os.path.join(venv_path,"lib64")
               if os.path.exists(lib64_path):
                  use_lib64 = True
            bld_env["VENV_USE_LIB64"] = use_lib64 # indicates the python running waf wants the 64-bit extent
            # Test for working symlinks
            dummy_target_path = os.path.join(venv_path,"dummy_target")
            dummy_symlink_path = os.path.join(venv_path,"dummy_symlink")
            try:
               os.makedirs(dummy_target_path)
               os.symlink(dummy_target_path,dummy_symlink_path)
            except:
               symlinks_work = False
               if debug_python_venv or debug_python_venv_symlinks:
                  Logs.pprint(debug_pyvenv_colour,"ensure_python_venv>>run(): failed.symlinks={!s}".format(symlinks_work))
            if os.path.exists(dummy_symlink_path):
               os.remove(dummy_symlink_path)
            if os.path.exists(dummy_target_path):
               os.rmdir(dummy_target_path)
            bld_env["VENV_SYMLINKS_WORK"] = symlinks_work
         if symlinks_work:
            if debug_python_venv or debug_python_venv_symlinks:
               msg = "ensure_python_venv>>run(symlinks=True): Creating ordinary python venv in {:s}"
               Logs.pprint(debug_pyvenv_colour,msg.format(venv_path))
            venv_builder = venv.EnvBuilder(symlinks=symlinks_work)
         else:
            # We only need the extension we're building to go under lib<whatever> (and nothing
            # from the base python),  so just override the EnvBuilder class with code that builds
            # both lib and lib64 as ordinary directories, and put our stuff in when it gets built.
            if debug_python_venv or debug_python_venv_symlinks:
               msg = "ensure_python_venv>>run(symlinks=False): Creating symlink-free python venv in {:s}"
               Logs.pprint(debug_pyvenv_colour,msg.format(venv_path))
            venv_builder = no_lib64_symlink_EnvBuilder(symlinks=symlinks_work)
         # FUTURE: check success of create() (nothing returned, maybe check existence of python binary?)
         venv_builder.create(venv_path)
      elif debug_python_venv or debug_python_venv_symlinks:
         Logs.pprint(debug_pyvenv_colour,"ensure_python_venv>>run() python executable already present")
      # Finally, make sure any extensions we're going to test are up to date.
      # The self.outputs[] nodes correspond to the self.inputs[] nodes after skipping the python executable at the start.
      if None != self.inputs:
         # Copy the latest build of the extensions into the venv's site-packages.
         use_lib64 = bld_env["VENV_USE_LIB64"]
         for ndx in range(len(self.inputs)):
            bld_ext_node = self.inputs[ndx]
            pkg_ext_node = self.outputs[ndx+1]
            bld_ext_path = bld_ext_node.abspath()
            pkg_ext_path = pkg_ext_node.abspath()
            if not os.path.exists(pkg_ext_path) or os.path.getmtime(bld_ext_path) > os.path.getmtime(pkg_ext_path):
               shutil.copyfile(bld_ext_path,pkg_ext_path)
            if use_lib64:
               pkg_ext_path = pkg_ext_path.replace("lib/python","lib64/python")
               if not os.path.exists(pkg_ext_path) or os.path.getmtime(bld_ext_path) > os.path.getmtime(pkg_ext_path):
                  shutil.copyfile(bld_ext_path,pkg_ext_path)
      return 0

class run_python_unit_test(Task.Task):
   color = 'CYAN'
   after = ['vnum','inst']
   vars=[]
   def __str__(self):
      # return "pyx_test_{:s}".format(self.ut_rel_name)
      return self.ut_rel_name
   def keyword(self):
      return "Testing"
   def runnable_status(self):
      ret = super(run_python_unit_test,self).runnable_status()
      if ret == Task.SKIP_ME:
         # Task has been run before (it is up to date).
         # Always run the unit tests again if they are runnable
         return Task.RUN_ME
      return ret
   def run(self):
      debug_me = getattr(self,"DEBUG_ME",False)
      num_venv_outputs = self.num_venv_outputs
      # Figure out what arguments to supply for the test
      # self.inputs[] is a list of nodes. -- These are the nodes required to exist and be up to date before this task can be run.
      # The first num_venv_outputs of self.inputs[] are the output nodes from ensure_python_venv.
      if hasattr(self,'inputs') and len(self.inputs) > num_venv_outputs:
         filename = self.inputs[num_venv_outputs].abspath() # filename is the first part of the line shown for results, should be an abspath()
         if debug_me:
            Logs.pprint("YELLOW","filename {{{:s}}}".format(filename))
      else:
         filename = getattr(self,'name',getattr(self,'_name','xyzzy'))
         if debug_me:
            Logs.pprint("YELLOW","task name {{{:s}}}".format(filename))
      if not hasattr(self,'ut_cwd'):
         Logs.pprint('RED','bailing, no working dir')
         return -1
      cwd = getattr(self,'ut_cwd',None)
      cwd_path = cwd.abspath()
      os.makedirs(cwd_path,mode=0o770,exist_ok=True)
      args = getattr(self,'ut_args',[])
      exec_full_name = self.inputs[0].abspath()
      if debug_me:
         Logs.pprint('PINK','cwd {{{:s}}} {:d}'.format(cwd_path,len(cwd_path)))
         Logs.pprint('PINK','exec full name {{{:s}}} {:d}'.format(exec_full_name,len(exec_full_name)))
         Logs.pprint('PINK','unit test name {{{:s}}} {:d}'.format(self.ut_test_name,len(self.ut_test_name)))
      if debug_me:
         for arg in args:
            Logs.pprint('PINK','      arg {{{:s}}} {:d}'.format(arg,len(arg)))
      if len(args) > 0:
         args = [exec_full_name] + args
      else:
         args = [exec_full_name]
      proc = Utils.subprocess.Popen(args,cwd=cwd_path,env=os.environ.copy(),stdin=Utils.subprocess.DEVNULL,
                                    stderr=Utils.subprocess.PIPE,stdout=Utils.subprocess.PIPE)
      (stdout,stderr) = proc.communicate()
      rc = proc.returncode
      # Logs.pprint('PINK','args {{{!s}}} -------> rc {:d}'.format(proc.args,rc))
      if debug_me:
         Logs.pprint('PINK','------->rc {:d}'.format(rc))
      if 0 == rc and hasattr(self,'ut_expected') and hasattr(self,'ut_actual'):
         # Compare the actual output to the expected output.
         diff_args = ['diff','-qba',self.ut_actual.abspath(),self.ut_expected.abspath()]
         diff_exec = self.generator.bld.env.DIFF
         if list == type(diff_exec):
            # Just take the first one.
            diff_exec = diff_exec[0]
         # Logs.pprint('YELLOW','type(diff_exec)={:s}'.format(type(diff_exec)))
         # Logs.pprint('YELLOW','type(cwd_path)={:s}'.format(type(cwd_path)))
         diff_proc = Utils.subprocess.Popen(diff_args,executable=diff_exec,cwd=cwd_path,env=os.environ.copy(),
                                            stderr=Utils.subprocess.PIPE,stdout=Utils.subprocess.PIPE)
         (diff_stdout,diff_stderr) = diff_proc.communicate()
         stdout += diff_stdout
         stderr += diff_stderr
         rc = diff_proc.returncode
      if hasattr(self,'ut_label') and filename != self.ut_label:
         filename += ' ('+self.ut_label+')'
      tup = (filename,rc,stdout,stderr)
      self.generator.utest_result = tup
      lib_unit_tests.testlock.acquire()
      try:
         bld = self.generator.bld
         Logs.debug("ut: %r",tup)
         try:
            bld.utest_results.append(tup)
         except AttributeError:
            bld.utest_results=[tup]
      finally:
         lib_unit_tests.testlock.release()
      if debug_me:
         Logs.pprint('YELLOW','finished {!s} {!s}'.format(self.ut_exec,args))
      return 0

# For any build target that contains the feature 'python_unit_test', add a call to gen_python_run()
# in order to try to generate two tasks (instance of ensure_python_venv followed by run_python_unit_test) that will run the test.
@feature('python_unit_test')
def gen_python_run(tgen):
   # Generate two tasks:
   # 1) an instance of ensure_python_venv with:
   #       inputs = any python extensions to be tested
   #       outputs = the python executable in the venv plus the venv/.../site-packages versions of the extensions
   # 2) an instance of run_python_unit_test with:
   #       inputs = the outputs of (1) plus the sources for this TaskGen
   # Note that by the time this gets executed, the BuildContext bld has had the bld.path reset to the top directory
   # (it's a context, and it changes), so we have to get the build node for the venv from the extensions or the sources.
   debug_me = getattr(tgen,'DEBUG_ME',False)
   if debug_me or debug_python_venv:
      Logs.pprint(debug_pyvenv_colour,"############################################# gen_python_run() entered")
      Logs.pprint(debug_pyvenv_colour,"tgen {{{!s}}}".format(tgen))
   bld = getattr(tgen,'bld',None)
   if None == bld:
      # The standard way to create a TaskGen is by calling Build.__call__() which sets the "bld" attribute.
      # If there is no "bld" attribute there is no telling how this was created or what is supposed to be run, so bail.
      return -1
   if debug_me or debug_python_venv:
      Logs.pprint(debug_pyvenv_colour,"type(bld) {{{!s}}}".format(type(bld)))
      Logs.pprint(debug_pyvenv_colour,"bld {{{!s}}}".format(bld))
      Logs.pprint(debug_pyvenv_colour,"bld.srcnode {{{!s}}}".format(bld.srcnode.abspath())) # S.B. top
      Logs.pprint(debug_pyvenv_colour,"bld.bldnode {{{!s}}}".format(bld.bldnode.abspath())) # S.B. out+variant
      Logs.pprint(debug_pyvenv_colour,"bld.path    {{{!s}}}".format(bld.path.abspath()))
      if hasattr(tgen,"orig_bld_path"):
         Logs.pprint(debug_pyvenv_colour,"orig_bld_path    {{{!s}}}".format(tgen.orig_bld_path.abspath()))
   # Find the length of the prefix of (i.e. filesystem path to) the top dir to use when building relative paths.
   abs_prefix_len = len(bld.srcnode.abspath()) + 1 # allow for trailing '/' on prefix
   bld_env = bld.env
   # --- Get the actual test script sources.
   srcs = getattr(tgen,'source',None)
   if debug_me:
      Logs.pprint(debug_pyvenv_colour,"abs_prefix_len={:d} tgen sources {{{!s}}}".format(abs_prefix_len,srcs))
   if srcs is None:
      # Nothing to do.
      return 0
   if not isinstance(srcs,list):
      srcs = [srcs]
   # --- Get any extensions being tested to use as a (possibly empty) list of inputs to ensure_python_venv.
   extensions_to_test = getattr(tgen,"extensions_to_test",[])
   # Make sure we have a (possibly empty) list of extensions to use as inputs to ensure_python_venv.
   if not isinstance(extensions_to_test,list):
      extensions_to_test = [extensions_to_test]
   # --- Construct the path to the venv we want (as mentioned above, bld.path does not help).
   venv_path = bld_env.VENV_PATH if "VENV_PATH" in bld_env else None
   if None == venv_path:
      if len(extensions_to_test) > 0:
         # Use the directory containing the first extension.
         venv_dir_node_parent = extensions_to_test[0].parent
         if debug_me or debug_python_venv:
            msg = "ensure_python_venv>>run(): new from extensions venv_dir {{{:s}}}"
            Logs.pprint(debug_pyvenv_colour,msg.format(venv_dir_node_parent.abspath()))
      else:
         # Fall back to the build directory corresponding to the first source.
         venv_dir_node_parent = srcs[0].parent.get_bld()
         if debug_me or debug_python_venv:
            msg = "ensure_python_venv>>run(): new from sources venv_dir {{{:s}}}"
            Logs.pprint(debug_pyvenv_colour,msg.format(venv_dir_node_parent.abspath()))
      venv_dir_node = venv_dir_node_parent.find_or_declare("venv")
      venv_path = venv_dir_node.abspath()
      if debug_me or debug_python_venv:
         Logs.pprint(debug_pyvenv_colour,"venv path {{{!s}}}".format(venv_path))
      ##if len(bld_env.VARIANT) > 0:
      ##   venv_path = os.path.join(venv_path,bld_env.VARIANT)
      ##   if debug_me or debug_python_venv:
      ##      Logs.pprint(debug_pyvenv_colour,"bldnode + variant path {{{!s}}}".format(venv_path))
      #venv_path = os.path.join(venv_path,bld.path.get_bld().path_from(bld.bldnode),"venv")
      #if debug_me or debug_python_venv:
      #   Logs.pprint(debug_pyvenv_colour,"bld.path {{{:s}}}".format(bld.path.abspath()))
      #   Logs.pprint(debug_pyvenv_colour,"bld.path.get_bld() {{{:s}}}".format(bld.path.get_bld().abspath()))
      #   msg = "ensure_python_venv>>run(): new type(venv_path) {{{!s}}} venv_path {{{!s}}}"
      #   Logs.pprint(debug_pyvenv_colour,msg.format(type(venv_path),venv_path))
      # Save the path for next time.
      bld_env["VENV_PATH"] = venv_path
   else:
      if debug_python_venv:
         msg = "ensure_python_venv>>run(): old type(venv_path) {{{!s}}} venv_path {{{!s}}}"
         Logs.pprint(debug_pyvenv_colour,msg.format(type(venv_path),venv_path))
      venv_dir_node = bld.bldnode.find_or_declare(venv_path)
   # --- Construct the list of outputs from ensure_python_venv (also used as inputs to run_python_unit_test).
   # Start with the python executable.
   if debug_python_venv:
      Logs.pprint(debug_pyvenv_colour,"ensure_python_venv>>run(): type(bld) {{{!s}}}".format(type(bld)))
   venv_outputs = [bld.bldnode.find_or_declare(os.path.join(venv_path,"bin","python"))]
   # Add any extensions.
   for ext_to_test in extensions_to_test:
      ext_test_bld_path = ext_to_test.abspath()
      ext_name = os.path.basename(ext_test_bld_path)
      ext_test_dst_path = os.path.join(venv_path,"lib","python"+bld_env.PYTHON_VERSION,"site-packages",ext_name)
      venv_outputs.append(bld.bldnode.find_or_declare(ext_test_dst_path))
   if debug_me:
      msg = "gen_python_run: ensure_python_venv has {:d} input(s), {:d} output(s)"
      Logs.pprint("CYAN",msg.format(len(extensions_to_test),len(venv_outputs)))
   # --- Create the ensure_python_venv task.
   epv = tgen.create_task("ensure_python_venv",extensions_to_test,venv_outputs)
   # --- Create a run_python_unit_test task for each src in srcs.
   for src in srcs:
      # Figure out the names of the test, both when running it and when showing the results.
      # The run time name should be relative to the top dir (e.g. start with "build/...."),
      # but the result time name should be absolute.
      src_path = src.abspath()
      ####TP
      test_abs_path = os.path.splitext(src.abspath())[0]
      test_rel_path = test_abs_path[abs_prefix_len:]
      test_name = os.path.splitext(os.path.basename(src_path))[0] # name too short
      if debug_me:
         Logs.pprint('CYAN','test name {{{:s}}} abs_path {{{:s}}} rel_path {{{:s}}}'.format(test_name,test_abs_path,test_rel_path))
      # Figure out the working directory (below build) for running the test, but keep it as a node,
      # because we probably have to create it, given that we won't put anything there except test output
      # and that happens after the test starts.
      twd = src.parent.get_bld()
      # Convert the test path to make it relative to the working directory.
      src_path = src.path_from(twd)
      if debug_me:
         Logs.pprint('CYAN','test directory {{{:s}}}'.format(twd.abspath()))
         Logs.pprint('CYAN','path to src {{{:s}}}'.format(src_path))
      if debug_me:
         Logs.pprint('CYAN','looking for input files for '+test_name+' in '+tgen.path.path_from(tgen.path.ctx.launch_node()))
      input_nodes = tgen.path.ant_glob('data/'+test_name+'/input/*.txt')
      dash_v = tgen.path.ant_glob('data/'+test_name+'/v')
      if len(input_nodes) > 0:
         if debug_me:
            Logs.pprint('CYAN','input files for '+test_name)
         for idn in input_nodes:
            # Assume output to be produced only if there is an expected file present in the source
            odn = None
            xdn = None
            idf = idn.abspath()
            fname = os.path.basename(idf)
            if None != bld:
               expected_output_name = 'data/'+test_name+'/expected/'+fname
               xdn = tgen.path.find_node(expected_output_name)
               if debug_me:
                  Logs.pprint('RED','searching for {{{:s}}} --> {:s}'.format(expected_output_name,type(xdn)))
               if None != xdn:
                  if debug_me:
                     Logs.pprint('RED','found known good node{{{:s}}}'.format(xdn.path_from(xdn.ctx.launch_node())))
                  # The output file needs to be in the build/variant directory, not the source directory, so use find_or_declare().
                  odn = tgen.path.find_or_declare('output/'+test_name+'/'+fname)
                  ####TP
                  test_abs_path = tgen.path.get_bld().abspath() + '/' + test_name + '/' + fname
                  test_rel_path = test_abs_path[abs_prefix_len:]
                  if debug_me:
                     msg = "input file, output node{{{:s}}} abs {{{:s}}} rel {{{:s}}}"
                     Logs.pprint('RED',msg.format(odn.path_from(odn.ctx.launch_node()),test_abs_path,test_rel_path))
            (fname,ext) = os.path.splitext(fname)
            if debug_me:
               Logs.pprint('CYAN','generating run_python_unit_test task for %s' % fname)
               Logs.pprint('CYAN','   input  {{{:s}}}'.format(idn.path_from(idn.ctx.launch_node())))
            # if None != odn: Logs.pprint('CYAN','   output {{{:s}}}'.format(odn.path_from(odn.ctx.launch_node())))
            ut_inputs = venv_outputs + [idn]
            ut_outputs = None if None == odn else [odn]
            rut = tgen.create_task('run_python_unit_test',ut_inputs,ut_outputs,num_venv_outputs=len(venv_outputs))
            # The task name should start from the build directory, not the abspath
            rut.ut_rel_name = test_rel_path
            rut._name = test_abs_path 
            rut.ut_cwd = twd
            rut.ut_test_name = test_name
            if debug_me:
               Logs.pprint('RED','test_name{{{:s}}} fname{{{:s}}}'.format(test_name,fname))
            if fname.startswith(test_name+'_'):
               fname = fname[len(test_name)+1:]
            rut.ut_label = fname if None == odn else fname+'{verified}'
            # we want to add the data file as input to the unit test run task (not the unit test build)
            # rut.ut_args = [src_path] + (['-v', '-f', idf] if len(dash_v) > 0 else ['-f', idf])
            rut.ut_args = [src_path]
            if None != odn:
               # There is expected output, so add the flag and path for actual output.
               rut.ut_args += ['-o', odn.abspath()]
               # Then tell the run_unit_test task to verify that actual == expected.
               rut.ut_actual = odn
               rut.ut_expected = xdn
      else:
         # No data files, just run the test program (there may still be expected output).
         if debug_me:
            Logs.pprint('CYAN','generating run_python_unit_test task for {{{:s}}} with no input files'.format(test_name))
         odn = None
         xdn = None
         fname = test_name
         if None != bld:
            # look for anything under the expected directory for output
            if len(bld.env.VARNAME) > 0:
               expected_output_name = 'data/'+test_name+'/expected/'+bld.env.VARNAME+'/*.txt'
               xdn = tgen.path.ant_glob(expected_output_name)
               if debug_me:
                  msg = 'searching {{{:s}}} for expected output {{{:s}}} --> {!s}'
                  Logs.pprint('RED',msg.format(tgen.path.abspath(),expected_output_name,type(xdn)))
            if None == xdn or 0 == len(xdn):
               expected_output_name = 'data/'+tgen.name+'/expected/*.txt'
               xdn = tgen.path.ant_glob(expected_output_name)
               if debug_me:
                  msg = 'searching {{{:s}}} for expected output {{{:s}}} --> {!s}'
                  Logs.pprint('RED',msg.format(tgen.path.abspath(),expected_output_name,type(xdn)))
            if None != xdn and len(xdn) > 0:
               if len(xdn) == 1:
                  xdn = xdn[0]
                  if debug_me:
                     Logs.pprint('RED','found known good node{{{:s}}}'.format(xdn.path_from(xdn.ctx.launch_node())))
                  # The output file needs to be in the build/variant directory, not the source directory, so use find_or_declare().
                  fname = os.path.basename(xdn.abspath())
                  odn = tgen.path.find_or_declare('output/'+test_name+'/'+fname)
                  ####TP
                  test_abs_path = tgen.path.get_bld().abspath() + '/' + test_name
                  test_rel_path = test_abs_path[abs_prefix_len:]
                  if debug_me:
                     msg = "no input file, output node{{{:s}}} abs {{{:s}}} rel {{{:s}}}"
                     Logs.pprint('RED',msg.format(odn.path_from(odn.ctx.launch_node()),test_abs_path,test_rel_path))
               elif len(xdn) > 1:
                  xdn = None
                  Logs.pprint('RED','{:s}: More than one expected output with no input (ignored)'.format(fname))
            else:
              if debug_me:
                  Logs.pprint('RED','no expected output found')
         ut_inputs = venv_outputs
         ut_outputs = None if None == odn else [odn]
         rut = tgen.create_task('run_python_unit_test',ut_inputs,ut_outputs,num_venv_outputs=len(venv_outputs))
         if debug_me:
            rut.DEBUG_ME = debug_me
            Logs.pprint('RED','gen_python_run: tasks generated')
         rut._name = test_abs_path # was test_name ==========================================================================
         rut.ut_rel_name = test_rel_path
         rut.ut_cwd = twd
         rut.ut_exec = os.path.join(bld.env.VENV_PATH,"bin","python")
         # rut.ut_exec = os.path.join(bld.env.VENV_PATH,"test_task")
         rut.ut_test_name = test_abs_path # was test_name
         rut.ut_label = fname if None == odn else fname+'{verified}'
         # rut.ut_args = [src_path] + (['-v'] if len(dash_v) > 0 else [])
         rut.ut_args = [src_path]
         if None != odn:
            # There is expected output, so add the flag and path for actual output.
            rut.ut_args += ['-o', odn.abspath()]
            # Then tell the run_unit_test task to verify that actual == expected.
            rut.ut_actual = odn
            rut.ut_expected = xdn
   # Make sure the results are displayed by adding the display function to the post-build functions if not already there.
   if hasattr(tgen,'bld'):
      if debug_me:
         Logs.pprint('CYAN','gen_run: found bld attr')
      if not hasattr(tgen.bld,'post_funs') or tgen.bld.show_test_results not in tgen.bld.post_funs:
         if debug_me:
            Logs.pprint('CYAN','gen_run: calling bld.add_post_fun(show_test_results)')
         tgen.bld.add_post_fun(tgen.bld.show_test_results)
