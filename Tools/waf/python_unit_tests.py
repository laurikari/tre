#=======================================================================================================
# Add functions and features for generating and running python extension unit tests.
#
import os
from waflib import TaskGen,Node,Task,Utils,Logs
from waflib.TaskGen import feature
# from waflib import Options

import lib_unit_tests

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
      debug_me = getattr(self,'DEBUG_ME',False)
      # Figure out what arguments to supply for the test
      # self.inputs[] is a list of nodes. -- These are the nodes required to exist and be up to date before this task can be run.
      if hasattr(self,'inputs') and len(self.inputs) > 0:
         filename = self.inputs[0].abspath() # filename is the first part of the line shown for results, should be an abspath()
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
      exec_full_name = getattr(self,'ut_exec',[filename])
      if debug_me:
         Logs.pprint('PINK','cwd {{{:s}}} {:d}'.format(cwd_path,len(cwd_path)))
         Logs.pprint('PINK','exec full name {{{:s}}} {:d}'.format(exec_full_name,len(exec_full_name)))
         Logs.pprint('PINK','unit test name {{{:s}}} {:d}'.format(self.ut_test_name,len(self.ut_test_name)))
      # if len(args) > 1:
      #    args = args[0:1] + [self.ut_test_name] + args[1:]
      # elif len(args) > 0:
      #    args = args[0:1] + [self.ut_test_name]
      # else:
      #    args = [self.ut_test_name]
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
# in order to try to generate a task (instance of run_python_unit_test) that will run the test.
@feature('python_unit_test')
def gen_python_run(tgen):
   debug_me = getattr(tgen,'DEBUG_ME',False)
   bld = getattr(tgen,'bld',None)
   if None == bld:
      abs_prefix_len = 0
   else:
      abs_prefix_len = len(bld.srcnode.abspath()) + 1 # allow for trailing '/' on prefix
   ut_exec = os.path.join(bld.env.VENV_PATH,"bin","python")
   srcs = getattr(tgen,'source',None)
   if debug_me:
      Logs.pprint('CYAN','tgen sources {{{!s}}}'.format(srcs))
   if srcs is None:
      # Nothing to do.
      return
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
            ut_inputs = [idn]
            ut_outputs = None if None == odn else [odn]
            rut = tgen.create_task('run_python_unit_test',ut_inputs,ut_outputs)
            # The task name should start from the build directory, not the abspath
            rut.ut_rel_name = test_rel_path
            rut._name = test_abs_path 
            rut.ut_exec = os.path.join(bld.env.VENV_PATH,"bin","python")
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
         # No data files, just run the test program.
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
         ut_inputs = []
         ut_outputs = None if None == odn else [odn]
         rut = tgen.create_task('run_python_unit_test',ut_inputs)
         if debug_me:
            rut.DEBUG_ME = debug_me
            Logs.pprint('RED','gen_python_run: task generated')
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
