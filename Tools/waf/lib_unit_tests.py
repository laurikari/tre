#=======================================================================================================
# Add functions and features for generating and running unit tests.
#
import os,sys
from waflib import TaskGen,Node,Task,Utils,Logs
from waflib.TaskGen import feature,after_method
# from waflib import Options
from waflib.Build import BuildContext
# Make sure we have the variant test results function on the BuildContext
import build_variants

testlock=Utils.threading.Lock()

# Task groups only apply to task generators, not individual tasks, so we can't use the feature and gen_run stuff
# in unit tests to put the unit tests into the test group, it has to be explicit in the wscript files.
# Add a couple of functions to the BuildContext so the switching and returning only takes two lines.
# FUTURE: Consider creating a new task generator in gen_run().

def switch_to_test_group(self,sub_group):
   # Switch to the task group for building and running unit tests.
   # Logs.pprint('CYAN','switching task group to {{{:s}}} from {{{:s}}}'.format(current_test_group,self.get_group_name(self.current_group)))
   self.set_group('test_{:s}_tasks'.format(sub_group))

# Patch the BuildContext class so that all instances have switch_to_test_group() as a method.
BuildContext.switch_to_test_group = switch_to_test_group

def return_to_build_group(self):
   # Return to the task group for building regular stuff.
   # msg = "switching task group back to {{{:s}}} from {{{:s}}}"
   # Logs.pprint('CYAN',msg.format(current_build_group,self.get_group_name(self.current_group)))
   self.set_group('build_tasks')

# Patch the BuildContext class so that all instances have return_to_build_group() as a method.
BuildContext.return_to_build_group = return_to_build_group

def show_test_results(self,bld):
   lst = getattr(bld, 'utest_results', [])
   # Logs.pprint('PINK','type(sys.stdout.encoding)={:s}'.format(type(sys.stdout.encoding)))
   # Logs.pprint('PINK','sys.stdout.encoding={!s}'.format(sys.stdout.encoding))
   # utf8_encoding = sys.stdout.encoding
   # Hmm, sys.stdout.encoding=ANSI_X3.4-1968 on my Linux
   utf8_encoding = 'utf-8'
   if lst:
      lst = sorted(lst, key=lambda t: t[0])
      Logs.pprint('CYAN','vvvvvvv Test execution summary for variant {:s}'.format(bld.env.VARNAME))
      Logs.pprint('YELLOW','        (these can be turned off by using the "--notest" command line option)')
      total = len(lst)
      tfail = len([x for x in lst if x[1]])
      tpass = total - tfail
      if tpass > 0:
         Logs.pprint('GREEN', '  tests that pass {0:d}/{1:d}'.format(tpass,total))
         for (f, code, out, err) in lst:
            if not code:
               Logs.pprint('GREEN', '    {0:s}'.format(f))
               # lines = out.decode('utf-8')
               # lines = out.decode('windows-1252')
               mark_end = False
               # We could use "ignore" instead of "backslashreplace".
               lines = out.decode(utf8_encoding,errors="backslashreplace").rstrip()
               if len(lines) > 0:
                  mark_end = True
                  Logs.pprint('GREEN', '    === stdout')
                  for line in lines.split('\r\n'):
                     Logs.pprint('GREEN', line)
               lines = err.decode(utf8_encoding,errors="backslashreplace").rstrip()
               if len(lines) > 0:
                  mark_end = True
                  Logs.pprint('GREEN', '    === stderr')
                  for line in lines.split('\r\n'):
                     Logs.pprint('GREEN', line)
               if mark_end:
                  Logs.pprint('GREEN', '    ^^^')
      if tfail > 0:
         Logs.pprint('PINK', '  tests that fail {0:d}/{1:d}'.format(tfail,total))
         for (f, code, out, err) in lst:
            if code:
               Logs.pprint('PINK', '    {0:s} -> {1:d}'.format(f,code))
               mark_end = False
               lines = out.decode(utf8_encoding,errors="backslashreplace").rstrip()
               if len(lines) > 0:
                  mark_end = True
                  Logs.pprint('PINK', '    === stdout')
                  for line in lines.split('\r\n'):
                     Logs.pprint('PINK', line)
               lines = err.decode(utf8_encoding,errors="backslashreplace").rstrip()
               if len(lines) > 0:
                  mark_end = True
                  Logs.pprint('PINK', '    === stderr')
                  for line in lines.split('\r\n'):
                     Logs.pprint('PINK', line)
               if mark_end:
                  Logs.pprint('PINK', '    ^^^')
      Logs.pprint('CYAN','^^^^^^^ end of summary for variant {:s}'.format(bld.env.VARNAME))
      # Get rid of test results in case they hold open files.
      bld.utest_results = None
      # Save the numbers for this variant.
      bld.add_variant_test_results(tpass,tfail)

# Patch the BuildContext class so that all instances have show_test_results() as a method.
BuildContext.show_test_results = show_test_results

class run_lib_unit_test(Task.Task):
   color = 'CYAN'
   after = ['vnum','inst']
   vars=[]
   def keyword(self):
      return "Testing"
   def runnable_status(self):
      ret = super(run_lib_unit_test,self).runnable_status()
      if ret == Task.SKIP_ME:
         # Task has been run before (it is up to date).
         # Always run the unit tests again if they are runnable
         return Task.RUN_ME
      return ret
   def run(self):
      # Figure out what executable to run for the test
      # self.inputs[] is a list of nodes. -- These are the nodes required to exist and be up to date before this task can be run.
      filename = self.inputs[0].abspath()
      args = getattr(self,'ut_args',[])
      self.ut_exec = getattr(self,'ut_exec',[filename])
      if getattr(self.generator,'ut_fun',None):
         self.generator.ut_fun(self)
      try:
         fu = getattr(self.generator.bld,'all_test_paths')
      except AttributeError:
         fu = os.environ.copy()
         self.generator.bld.all_test_paths = fu
         lst=[]
         for g in self.generator.bld.groups:
            for tg in g:
               if getattr(tg,'link_task',None):
                  lst.append(tg.link_task.outputs[0].parent.abspath())
         def add_path(dct,path,var):
            dct[var] = os.pathsep.join(Utils.to_list(path)+[os.environ.get(var,'')])
         if Utils.is_win32:
            add_path(fu,lst,'PATH')
         elif Utils.unversioned_sys_platform()=='darwin':
            add_path(fu,lst,'DYLD_LIBRARY_PATH')
            add_path(fu,lst,'LD_LIBRARY_PATH')
         else:
            add_path(fu,lst,'LD_LIBRARY_PATH')
      cwd = getattr(self.generator,'ut_cwd','') or self.inputs[0].parent.abspath()
      exec_full_name = self.ut_exec[0]
      ## Logs.pprint('PINK','cwd {{{:s}}} {:d}'.format(cwd,len(cwd)))
      ## Logs.pprint('PINK','exec full name {{{:s}}} {:d}'.format(exec_full_name,len(exec_full_name)))
      ## Logs.pprint('PINK','unit test name {{{:s}}} {:d}'.format(self.ut_test_name,len(self.ut_test_name)))
      if len(args) > 0:
         args = [self.ut_test_name] + args
      else:
         args = [self.ut_test_name]
      ## for arg in args:
      ##    Logs.pprint('PINK','      arg {{{:s}}} {:d}'.format(arg,len(arg)))
      proc = Utils.subprocess.Popen(args,executable=exec_full_name,cwd=cwd,env=fu,stderr=Utils.subprocess.PIPE,stdout=Utils.subprocess.PIPE)
      (stdout,stderr) = proc.communicate()
      rc = proc.returncode
      if 0 == rc and hasattr(self,'ut_expected') and hasattr(self,'ut_actual'):
         # Compare the actual output to the expected output.
         diff_args = ['diff','-qba',self.ut_actual.abspath(),self.ut_expected.abspath()]
         diff_exec = self.generator.bld.env.DIFF
         # Logs.pprint('YELLOW','type(diff_exec)={:s}'.format(type(diff_exec)))
         if list == type(diff_exec):
            # Just take the first one.
            diff_exec = diff_exec[0]
         # Logs.pprint('YELLOW','type(cwd)={:s}'.format(type(cwd)))
         diff_proc = Utils.subprocess.Popen(diff_args,executable=diff_exec,cwd=cwd,env=fu,stderr=Utils.subprocess.PIPE,stdout=Utils.subprocess.PIPE)
         (diff_stdout,diff_stderr) = diff_proc.communicate()
         stdout += diff_stdout
         stderr += diff_stderr
         rc = diff_proc.returncode
      if hasattr(self,'ut_label'):
         filename += ' ('+self.ut_label+')'
      tup = (filename,rc,stdout,stderr)
      self.generator.utest_result = tup
      testlock.acquire()
      try:
         bld = self.generator.bld
         Logs.debug("ut: %r",tup)
         try:
            bld.utest_results.append(tup)
         except AttributeError:
            bld.utest_results=[tup]
      finally:
         testlock.release()

# For any build target that contains the feature 'lib_unit_test', add a call to gen_run() after
# the call to apply_link() in order to try to generate a task (instance of run_lib_unit_test) that
# will run the link output as a unit test.
@feature('lib_unit_test')
@after_method('apply_link')
def gen_run(tgen):
   debug_expected_output = getattr(tgen,"DEBUG_ME",False)
   if getattr(tgen,'link_task',None):
      if debug_expected_output:
         Logs.pprint('CYAN','looking for input files for '+tgen.name+' in '+tgen.path.path_from(tgen.path.ctx.launch_node()))
         Logs.pprint('CYAN','   tgen.path = {{{!s}}}'.format(tgen.path.abspath()))
      bld = getattr(tgen,'bld',None)
      input_nodes = []
      if None != bld and len(bld.env.VARNAME) > 0:
         # We're building a variant, look for variant specific input (under the VARNAME (i.e. '_'s) not the path).
         input_nodes = tgen.path.ant_glob('data/'+tgen.name+'/input/'+bld.env.VARNAME+'/*.txt')
         # The 'v' is just a boolean indicator, it could be a directory or file.
         dash_v = tgen.path.ant_glob('data/'+tgen.name+'/input/'+bld.env.VARNAME+'/v')
      if len(input_nodes) <= 0:
         # This isn't a variant, or the input isn't variant specific.
         input_nodes = tgen.path.ant_glob('data/'+tgen.name+'/input/*.txt')
         dash_v = tgen.path.ant_glob('data/'+tgen.name+'/v')
      if len(input_nodes) > 0:
         if debug_expected_output:
            Logs.pprint('CYAN','input files for '+tgen.name)
         for idn in input_nodes:
            # Assume output to be produced only if there is an expected file present in the source
            odn = None
            xdn = None
            idf = idn.abspath()
            fname = os.path.basename(idf)
            if None != bld:
               if debug_expected_output:
                  Logs.pprint('CYAN','looking for expected output files for '+tgen.name+' in '+tgen.path.abspath())
               if "PLATSYS" in bld.all_envs['']:
                  platsys = bld.all_envs[''].PLATSYS
                  if len(bld.env.VARNAME) > 0:
                     expected_output_name = 'data/'+platsys+'/'+tgen.name+'/expected/'+bld.env.VARNAME+'/'+fname
                     xdn = tgen.path.find_node(expected_output_name)
                     if debug_expected_output:
                        msg = 'searching {{{:s}}} for expected output {{{:s}}} --> {!s}'
                        Logs.pprint('RED',msg.format(tgen.path.abspath(),expected_output_name,type(xdn)))
                  if None == xdn:
                     expected_output_name = 'data/'+platsys+'/'+tgen.name+'/expected/'+fname
                     xdn = tgen.path.find_node(expected_output_name)
                     if debug_expected_output:
                        msg = 'searching {{{:s}}} for expected output {{{:s}}} --> {!s}'
                        Logs.pprint('RED',msg.format(tgen.path.abspath(),expected_output_name,type(xdn)))
               if None == xdn and len(bld.env.VARNAME) > 0:
                  expected_output_name = 'data/'+tgen.name+'/expected/'+bld.env.VARNAME+'/'+fname
                  xdn = tgen.path.find_node(expected_output_name)
                  if debug_expected_output:
                     Logs.pprint('RED','searching for {{{:s}}} (expected output) --> {!s}'.format(expected_output_name,type(xdn)))
               if None == xdn:
                  expected_output_name = 'data/'+tgen.name+'/expected/'+fname
                  xdn = tgen.path.find_node(expected_output_name)
                  if debug_expected_output:
                     Logs.pprint('RED','searching for {{{:s}}} (expected output) --> {!s}'.format(expected_output_name,type(xdn)))
               if None != xdn:
                  if debug_expected_output:
                     Logs.pprint('RED','found expected (known good) node{{{:s}}}'.format(xdn.path_from(xdn.ctx.launch_node())))
                  # The output file needs to be in the build/variant directory, not the source directory, so use find_or_declare().
                  # We don't need the variant in the output file path because the build/variant directory already has it.
                  actual_output_name = 'output/'+tgen.name+'/'+fname
                  odn = tgen.path.find_or_declare(actual_output_name)
                  if debug_expected_output:
                     Logs.pprint('RED','output node{{{:s}}}'.format(odn.path_from(odn.ctx.launch_node())))
            (fname,ext) = os.path.splitext(fname)
            if debug_expected_output:
               Logs.pprint('CYAN','generating run_lib_unit_test task for %s' % fname)
               Logs.pprint('CYAN','   input  {{{:s}}}'.format(idn.path_from(idn.ctx.launch_node())))
               if None != odn: Logs.pprint('CYAN','   output {{{:s}}}'.format(odn.path_from(odn.ctx.launch_node())))
            # Get rid of windows noise about foo.manifest if present.
            ut_inputs = [x for x in tgen.link_task.outputs if not x.abspath().lower().endswith('.manifest')] + [idn]
            ut_outputs = None if None == odn else [odn]
            rut = tgen.create_task('run_lib_unit_test',ut_inputs,ut_outputs)
            rut.ut_test_name = tgen.name
            # Logs.pprint('RED','tgen.name{{{:s}}} fname{{{:s}}}'.format(tgen.name,fname))
            if fname.startswith(tgen.name+'_'):
               fname = fname[len(tgen.name)+1:]
            rut.ut_label = fname if None == odn else fname+'{verified}'
            # we want to add the data file as input to the unit test run task (not the unit test build)
            rut.ut_args = ['-v', '-f', idf] if len(dash_v) > 0 else ['-f', idf]
            if None != odn:
               # There is expected output, so add the flag and path for actual output.
               rut.ut_args += ['-o', odn.abspath()]
               # Then tell the run_lib_unit_test task to verify that actual == expected.
               rut.ut_actual = odn
               rut.ut_expected = xdn
      else:
         if debug_expected_output:
            Logs.pprint('CYAN','no input files for '+tgen.name)
         # No data files, just run the test program.
         # Logs.pprint('CYAN','generating run_lib_unit_test task for %s with no input files' % tgen.name)
         odn = None
         xdn = None
         fname = tgen.name
         if None != bld:
            # look for anything under the expected directory for output
            if "PLATSYS" in bld.all_envs['']:
               platsys = bld.all_envs[''].PLATSYS
               if len(bld.env.VARNAME) > 0:
                  expected_output_name = 'data/'+platsys+'/'+tgen.name+'/expected/'+bld.env.VARNAME+'/*.txt'
                  xdn = tgen.path.ant_glob(expected_output_name)
                  if debug_expected_output:
                     msg = 'searching {{{:s}}} for expected output {{{:s}}} --> {!s}'
                     Logs.pprint('RED',msg.format(tgen.path.abspath(),expected_output_name,type(xdn)))
               if None == xdn or 0 == len(xdn):
                  expected_output_name = 'data/'+platsys+'/'+tgen.name+'/expected/*.txt'
                  xdn = tgen.path.ant_glob(expected_output_name)
                  if debug_expected_output:
                     msg = 'searching {{{:s}}} for expected output {{{:s}}} --> {!s}'
                     Logs.pprint('RED',msg.format(tgen.path.abspath(),expected_output_name,type(xdn)))
            if (None == xdn or 0 == len(xdn)) and len(bld.env.VARNAME) > 0:
               expected_output_name = 'data/'+tgen.name+'/expected/'+bld.env.VARNAME+'/*.txt'
               xdn = tgen.path.ant_glob(expected_output_name)
               if debug_expected_output:
                  msg = 'searching {{{:s}}} for expected output {{{:s}}} --> {!s}'
                  Logs.pprint('RED',msg.format(tgen.path.abspath(),expected_output_name,type(xdn)))
            if None == xdn or 0 == len(xdn):
               expected_output_name = 'data/'+tgen.name+'/expected/*.txt'
               xdn = tgen.path.ant_glob(expected_output_name)
               if debug_expected_output:
                  msg = 'searching {{{:s}}} for expected output {{{:s}}} --> {!s}'
                  Logs.pprint('RED',msg.format(tgen.path.abspath(),expected_output_name,type(xdn)))
            if None != xdn and len(xdn) > 0:
               if len(xdn) == 1:
                  xdn = xdn[0]
                  if debug_expected_output:
                     Logs.pprint('RED','found expected (known good) node{{{:s}}}'.format(xdn.path_from(xdn.ctx.launch_node())))
                  # The output file needs to be in the build/variant directory, not the source directory, so use find_or_declare().
                  # We don't need the variant in the output file path because the build/variant directory already has it.
                  fname = os.path.basename(xdn.path_from(xdn.ctx.launch_node()))
                  odn = tgen.path.find_or_declare('output/'+tgen.name+'/'+fname)
                  if debug_expected_output:
                     Logs.pprint('RED','output node{{{:s}}}'.format(odn.path_from(odn.ctx.launch_node())))
               elif len(xdn) > 1:
                  xdn = None
                  Logs.pprint('RED','{:s}: More than one expected output with no input (ignored)'.format(fname))
            else:
               if debug_expected_output:
                  Logs.pprint('RED','no expected output found')
         else:
            if debug_expected_output:
               Logs.pprint('RED','no bld, cannot look for expected output')
         # Get rid of windows noise about foo.manifest if present.
         ut_inputs = [x for x in tgen.link_task.outputs if not x.abspath().lower().endswith('.manifest')]
         ut_outputs = None if None == odn else [odn]
         rut = tgen.create_task('run_lib_unit_test',ut_inputs)
         rut.ut_test_name = tgen.name
         rut.ut_label = fname if None == odn else fname+'{verified}'
         rut.ut_args = ['-v'] if len(dash_v) > 0 else []
         if None != odn:
            # There is expected output, so add the flag and path for actual output.
            rut.ut_args += ['-o', odn.abspath()]
            # Then tell the run_lib_unit_test task to verify that actual == expected.
            rut.ut_actual = odn
            rut.ut_expected = xdn
      # Make sure the results are displayed by adding the display function to the post-build functions if not already there.
      if hasattr(tgen,'bld'):
         # Logs.pprint('CYAN','gen_run: found bld attr')
         if not hasattr(tgen.bld,'post_funs') or tgen.bld.show_test_results not in tgen.bld.post_funs:
            # Logs.pprint('CYAN','gen_run: calling bld.add_post_fun(show_test_results)')
            tgen.bld.add_post_fun(tgen.bld.show_test_results)
