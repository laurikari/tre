#=======================================================================================================
# Create the different build type commands.
# waf normally has a plain build command (e.g. "waf build"), but we want
# to be able to either:
#    1) build the variants directly (e.g. "waf build_dbg64"), or
#    2) choose the variant(s) by means of options (e.g. "waf --dbg --64 build" or "waf build --rel --32").
# We do this by creating a bunch of variant specific commands (for (1)), and wrapping the "bare" commands
# in a function that redirects to some of the variants, depending on the options (for (2)).
#
from waflib import Options,Logs
# Import the commands/classes we are going to wrap/clone.
from waflib.Build import BuildContext, CleanContext, InstallContext, UninstallContext, ListContext, StepContext
bciuls_tuple = (BuildContext, CleanContext, InstallContext, UninstallContext, ListContext, StepContext)

debug_build_all = False
debug_build_variants = False
debug_build_variant_queuing = False
debug_install = False
debug_bv_colour = "YELLOW"
debug_bi_colour = "YELLOW"

variant_test_results = None

def add_variant_test_results(bld,tpass,tfail):
   global variant_test_results
   if None != variant_test_results:
      variant_test_results[bld.env.VARNAME] = (tpass,tfail)

BuildContext.add_variant_test_results = add_variant_test_results

def show_variant_test_summary(bld):
   global variant_test_results
   summary_colour = "CYAN"
   failure_colour = "PINK"
   Logs.pprint(summary_colour,"========================================================")
   # Logs.pprint(summary_colour," {:d} variants tested".format(len(variant_test_results)))
   if len(variant_test_results) > 0:
      tpass = 0
      tfail = 0
      vpass = 0
      vfail = 0
      for key in variant_test_results:
         res_tup = variant_test_results[key]
         tpass += res_tup[0]
         tfail += res_tup[1]
         if res_tup[1] > 0:
            vfail += 1
         else:
            vpass += 1
      if vfail > 0:
         Logs.pprint(failure_colour," {:d} variants tested, {:d} passed, {:d} failed".format(len(variant_test_results),vpass,vfail))
      else:
         Logs.pprint(summary_colour," {:d} variants tested, {:d} passed, {:d} failed".format(len(variant_test_results),vpass,vfail))
      for key in variant_test_results:
         res_tup = variant_test_results[key]
         nt = res_tup[0] + res_tup[1]
         if res_tup[1] > 0:
            Logs.pprint(failure_colour,"  Variant {:s}: {:d} tests, {:d} passed, {:d} failed".format(key,nt,res_tup[0],res_tup[1]))
         else:
            Logs.pprint(summary_colour,"  Variant {:s}: {:d} tests, {:d} passed, {:d} failed".format(key,nt,res_tup[0],res_tup[1]))

# BuildContext.show_variant_test_summary = show_variant_test_summary

def construct_variant_names(variant_group_list):
   # Construct a list of (name,path) tuples for the variants.
   # This is called shortly after importing this module as part of reading the wscript file.
   variant_name_path_list = []
   variant_count = 1
   for vgroup in variant_group_list:
      variant_count = variant_count * len(vgroup)
   lenvgl = len(variant_group_list)
   vx = [0 for i in range(lenvgl)]
   for vn in range(variant_count):
      # Build a variant name/path using the current index values in vx[] applied to variant_group_list.
      name_components = []
      for i in range(lenvgl):
         # Logs.pprint("GREEN","vgl[{:d}][{:d}] {!s}".format(i,vx[i],variant_group_list[i][vx[i]]))
         name_components.append(variant_group_list[i][vx[i]])
      # Logs.pprint("GREEN","name components {!s}".format(name_components))
      # Construct the variant name and path from the name components.
      # The name is going to be used for the variant build command and function names, so no '/'s.
      variant_name_path_list.append(("_".join(name_components),"/".join(name_components)))
      # Increment the values in vx[] for the next name/path.
      for i in range(lenvgl):
         vx[i] += 1
         if vx[i] < len(variant_group_list[i]):
            # Finished incrementing.
            break
         # Start over at 0 and continue incrementing (i.e. "carry" to the next column).
         vx[i] = 0
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"variant_name_path_list {!s}".format(variant_name_path_list))
   return(variant_name_path_list)

def create_variants(cfg,variant_group_list,variant_name_path_list):
   # Create env variants for everything in the variant_name_path_list.
   # This is called from within the configure() step.
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"Entered create_variants()")
      Logs.pprint(debug_bv_colour,"type(cfg) {{{!s}}}".format(type(cfg)))
      Logs.pprint(debug_bv_colour,"type(cfg.env) {{{!s}}}".format(type(cfg.env)))
      Logs.pprint(debug_bv_colour,"type(cfg.all_envs) {{{!s}}}".format(type(cfg.all_envs)))
      Logs.pprint(debug_bv_colour,"len(cfg.all_envs) {:d}".format(len(cfg.all_envs)))
      Logs.pprint(debug_bv_colour,"existing variants:")
      for cfg_key in cfg.all_envs:
          Logs.pprint(debug_bv_colour,"  key {{{:s}}}".format(cfg_key))
   original_env = cfg.env
   original_env.VARNAME = ""
   original_env.VARIANT = ""
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"--------------------- original_env:\n{!s}".format(original_env))
   for vnp in variant_name_path_list:
      # Extract the variant name and path from vnp.
      bld_variant_name = vnp[0]
      bld_variant_path = vnp[1]
      # Logs.pprint("YELLOW","variant name {:s}".format(bld_variant_name))
      # Logs.pprint("PINK","variant path {:s}".format(bld_variant_path))
      # Copy the original environment and set the key for finding it to be the bld_variant_path.
      # Do not use native_path() for this, as waf will force '/'s anyways.
      # Note that conf.setenv() sets the class variable cfg.variant
      cfg.setenv(bld_variant_path,original_env)
      cfg.env.VARNAME = bld_variant_name
      cfg.env.VARIANT = bld_variant_path
      cfg.env.viable = True # Assume this variant is OK until we figure out otherwise.
      # Set boolean "variant_VVVV" flags for each of the variants VVVV in each of the variant groups.
      for vgx in range(len(variant_group_list)):
         vgroup = variant_group_list[vgx]
         for vx in range(len(vgroup)):
            vname = vgroup[vx]
            cfg.env["variant_"+vname] = (vname in bld_variant_path)
   # Go back to the env we started with.
   cfg.setenv("")
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"Finished create_variants()")

def create_variant_commands(variant_name_path_list):
   # Clone the base commands for the variants.
   # This is called just after calling construct_variant_names(variant_group_list) above.
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"Entered create_variant_commands()")
   for vnp in variant_name_path_list:
      bld_variant_name = vnp[0]
      bld_variant_path = vnp[1]
      if debug_build_variants:
         # Clone the various commands by changing the class/method name with the following bit of magic:
         Logs.pprint(debug_bv_colour,"cloning for name {:s} path {!s}".format(bld_variant_name,bld_variant_path))
      # For each waf 'command' (actually Python class),
      for bciuls_ctx in bciuls_tuple: 
         if not bciuls_ctx.__name__.startswith("build_"):
            from_name = bciuls_ctx.__name__.replace('Context','').lower()
            to_name = from_name + '_' + bld_variant_name
            if debug_build_variants:
               Logs.pprint(debug_bv_colour,"for {{{:s}}} clone {{{:s}}} --> {{{:s}}}".format(bciuls_ctx.__name__,from_name,to_name))
            # define a subclass of bciuls_ctx with the appropriate cmd and variant.
            class tmp(bciuls_ctx):
               # Note that we are setting the CLASS variables here!
               cmd = to_name
               # Setting the class variable variant will end up appending the variant
               # to the build path, so here we need to have embedded '/'s.
               # It is also used as the key to locate the configured environment.
               # Note that waf forces the use of '/' in the path used as the environment key.
               variant = bld_variant_path
               def __setattr__(self,name,value):
                  if getattr(self,"DEBUG_PATH",False) and "path" == name:
                     Logs.pprint("RED","setting path attr for {{{!s}}} to {{{!s}}}".format(self,value))
                  object.__setattr__(self,name,value)
   bciuls_ctx = bciuls_tuple[0]
   if not bciuls_ctx.__name__.startswith("build_"):
      from_name = bciuls_ctx.__name__.replace('Context','').lower()
      to_name = from_name + "_test_summary"
      if debug_build_variants:
         Logs.pprint(debug_bv_colour,"for {{{:s}}} clone {{{:s}}} --> {{{:s}}}".format(bciuls_ctx.__name__,from_name,to_name))
      # define a subclass of BuildContext with the appropriate cmd.
      class tmp(bciuls_ctx):
         # Note that we are setting the CLASS variables here!
         cmd = to_name
         variant = None
         #def build(bld):
         #   bld.show_variant_test_summary()
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"Finished create_variant_commands()")

def variant_decorator(platsys,func_to_decorate,variant_group_list):
   # This should be private to this module (only called by redirect_to_variants(variant_group_list) below).
   def variant_wrapper(*args,**kwargs):
      global variant_test_results
      queue_msg_colour = 'BLUE'   # See waflib/Logs.py colors_lst for available colours.
      # Get the Context for this command.
      ctx = args[0]
      orig_env = ctx.env          # Configset from the original configuration command
      command = ctx.cmd
      default_build_variant = orig_env.default_variant_name
      if debug_build_variants or debug_build_variant_queuing or debug_build_all:
         Logs.pprint(debug_bv_colour,"Entered variant_wrapper(...), type(ctx) {{{!s}}}".format(type(ctx)))
         Logs.pprint(debug_bv_colour,"   variant {{{!s}}} VGL {{{!s}}}".format(ctx.variant,variant_group_list))
         Logs.pprint(debug_bv_colour,"   cmd {{{!s}}}".format(ctx.__class__.cmd))
         Logs.pprint("PINK","   ctx.all_envs {{{!s}}}".format(type(ctx.all_envs)))
         Logs.pprint("PINK","   len(ctx.all_envs) {:d}".format(len(ctx.all_envs)))
         Logs.pprint("PINK","   default_variant_name {:s}".format((default_build_variant)))
         if debug_build_variants:
            for cfg_key in ctx.all_envs:
               Logs.pprint(debug_bv_colour,"--------- cfg_key {{{:s}}}".format(cfg_key))
      if ctx.__class__.cmd.startswith("install"):
         # We only want to install one variant.
         if debug_install:
            Logs.pprint(debug_bi_colour,"entered install wrapper")
         if ctx.variant and len(ctx.variant) > 0:
            # A specific variant, just do the requested install.
            if debug_install:
               Logs.pprint(debug_bi_colour,"variant not empty, go with existing fn")
            ret_val = func_to_decorate(*args,**kwargs)
            return ret_val
         # This is the original unmodified install command, but we only want to install ONE variant,
         # so queue the default and not anything else.
         Logs.pprint(queue_msg_colour,'Queuing {:s}/{:s}/{:s} (default)'.format(command,platsys,default_build_variant))
         default_install = command+"_"+default_build_variant
         # Do the actual command pushing (Options.commands contains any following arguments from the command line).
         if debug_install:
            Logs.pprint(debug_bi_colour,"Queued command: {{{!s}}}".format(default_install))
         Options.commands = [default_install] + Options.commands
         # Do NOT proceed with the wrapped function when there is no variant.
         return None
      if ctx.variant and len(ctx.variant) > 0:
         # The build context has a variant set, so just call the appropriate function (one of the ones created by create_variant_commands()).
         if debug_build_variants or debug_build_variant_queuing or debug_build_all:
            Logs.pprint(debug_bv_colour,"variant not empty, go with existing fn")
         ret_val = func_to_decorate(*args,**kwargs)
         return ret_val
      if ctx.__class__.cmd.startswith("build_test_summary"):
         # This is the test summary, show the test results and don't queue anything.
         if debug_build_variants or debug_build_variant_queuing:
            Logs.pprint(debug_bv_colour,"test_summary, go with show_summary fn")
         ret_val = show_variant_test_summary(ctx)
         return ret_val
      # No variant (this is the original non-variant command), push variants of the ctx.cmd onto
      # the command stack depending on both the current options set and those set during the configuration.
      if debug_build_variants or debug_build_variant_queuing or debug_build_all:
         Logs.pprint(debug_bv_colour,"type(variant_test_results) {!s}".format(type(variant_test_results)))
      variant_test_results = dict()
      variant_commands = []
      curr_opt = Options.options  # options from the command line for this build
      # Build all the variants if (a) explicitly enabled for this command,
      # or (b) not explicitly disabled for both this command and the eariler configuration.
      build_all = (curr_opt.build_all_variants > 0 or
                   (curr_opt.build_all_variants == 0 and getattr(orig_env,"build_default_build_all_variants",0) >= 0))
      if debug_build_all:
         msg = "build_all {!s}, co.build_all_variants={:d} default_build_all_variants={:d}"
         Logs.pprint(debug_bv_colour,msg.format(build_all,curr_opt.build_all_variants,getattr(orig_env,"build_default_build_all_variants",0)))
         Logs.pprint(debug_bv_colour,"default_build_variant type={!s} val {{{!s}}}".format(type(default_build_variant),default_build_variant))
      requested_variants = []
      variant_count = 1
      # Look at the current options (in oo) and the configured options (in ctx) to figure out which ones we want.
      for vgroup in variant_group_list:
         v = []
         for vname in vgroup:
            # We want to build this variant if:
            #    (a)   it was enabled in the current options (i.e. on the command line for this build), or
            #    (b)   it was enabled in the original configuration and not disabled on the command line of this build
            # values are -1 if disabled, +1 if enabled, 0 if not mentioned
            cov = getattr(curr_opt,"enable_"+vname,0)
            bde_name = "build_default_enable_" + vname
            ocv = 0 if bde_name not in orig_env else orig_env[bde_name]
            if debug_build_variants or debug_build_variant_queuing:
               msg = "vname {{{!s}}} type(cov)={{{!s}}} {!s} type(ocv)={{{!s}}} {!s}"
               Logs.pprint(debug_bv_colour,msg.format(vname,type(cov),cov,type(ocv),ocv))
            if build_all or cov > 0 or (ocv > 0 and cov == 0):
               v += [vname]
         if 0 == len(v):
            # We must have at least one from each group, so take the first.
            v += [vgroup[0]]
         requested_variants.append(v)
         variant_count *= len(v)
      # At this point requested_variants looks like variant_group_list except some of the groups might be smaller (no group is empty though).
      if debug_build_variants or debug_build_variant_queuing:
         Logs.pprint(debug_bv_colour,"requested_variants {{{!s}}} len={:d}".format(requested_variants,len(requested_variants)))
      # -------------------------------
      rvlen = len(requested_variants) # Should be the same as len(variant_group_list)
      vx = [0 for i in range(rvlen)]
      for vn in range(variant_count):
         # Build a variant name/path using the current index values in vx[] applied to requested variants.
         name_components = []
         for i in range(rvlen):
            name_components.append(requested_variants[i][vx[i]])
         if debug_build_variants or debug_build_variant_queuing:
            Logs.pprint(debug_bv_colour,"name_components {{{!s}}} for vn={:d}".format(name_components,vn))
         # Add the appropriate command variant to the list of commands we're going to queue.
         bld_variant_name = "_".join(name_components)
         bld_variant_path = "/".join(name_components)
         if ctx.all_envs[bld_variant_path].viable and (build_all or default_build_variant == bld_variant_name):
            Logs.pprint(queue_msg_colour,"Queuing {:s}/{:s}/{:s}".format(command,platsys,bld_variant_path))
            variant_commands += [command+"_"+bld_variant_name]
         else:
            Logs.pprint(queue_msg_colour,"Skipping {:s}/{:s}/{:s} (not requested or not viable)".format(command,platsys,bld_variant_path))
         # Increment the values in vx[] for the next name/path.
         for i in range(rvlen):
            vx[i] += 1
            if vx[i] < len(requested_variants[i]):
               # Finished incrementing.
               break
            # Start over at 0 and continue incrementing (i.e. "carry" to the next column).
            vx[i] = 0
      if len(variant_commands) == 0:
         # No options set, use a default (only here in case the options(opt) function
         # is messed up and does not provide a set of options).
         Logs.pprint(queue_msg_colour,'Queuing {:s}/{:s}/{:s} (default)'.format(command,platsys,default_build_variant))
         variant_commands = [command+"_"+default_build_variant]
      # -----------------
      # Add a function to summarize test results if more than one variant was queued.
      if debug_build_variants:
         Logs.pprint(debug_bv_colour,"opt.enable_tests: {{{!s}}}".format(curr_opt.enable_tests ))
         Logs.pprint(debug_bv_colour,"build_default_enable_tests {{{!s}}}".format(orig_env.build_default_enable_test))
      if len(variant_commands) > 1 and (curr_opt.enable_tests or
                                        (hasattr(orig_env,"build_default_enable_tests") and orig_env.build_default_enable_tests)):
         summary_command_name = command+"_test_summary"
         Logs.pprint(queue_msg_colour,"Queuing {:s}".format(summary_command_name))
         variant_commands += [summary_command_name]
      # -----------------
      # Do the actual command pushing (Options.commands contains any following arguments from the command line).
      if debug_build_variants or debug_build_variant_queuing:
         Logs.pprint(debug_bv_colour,"Queued commands: {{{!s}}}".format(variant_commands))
      Options.commands = variant_commands + Options.commands
      # Do NOT proceed with the wrapped function when there is no variant, because at least
      # for the 'clean' case this will end up removing ALL variants, plus removing/altering
      # files needed to run waf commands, making 'waf distclean configure' necessary.
      # Logs.info('variant_wrapper finished, skipping wrapped function, cmd={0:s} variant={1:s}'.format(ctx.cmd,ctx.variant))
      return None
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"Entered variant_decorator(), returning variant_wrapper")
   return variant_wrapper

def redirect_to_variants(platsys,variant_group_list):
   # Install the wrapper we are using to redirect the "bare" commands to the variants.
   # This is called just after calling create_variant_commands(variant_name_path_list) above.
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"Entered redirect_to_variants()")
   for bciuls_ctx in bciuls_tuple:
      cmd_getting_wrapped = bciuls_ctx.cmd
      if debug_build_variants:
         Logs.pprint('PINK','redirecting {:s} for {{{!s}}}.'.format('execute',cmd_getting_wrapped))
      # The BuildContext.execute() fn loads the all_envs dictionary (if not already loaded), then calls BuildContext.execute_build().
      # If the variant wrapper needs to look at the envs, we need to wrap execute_build(), otherwise wrapping execute() is good enough.
      #func_to_wrap = bciuls_ctx.execute
      func_to_wrap = bciuls_ctx.execute_build
      if 'variant_wrapper' == func_to_wrap.__name__:
         if debug_build_variants:
            msg = "Function {:s} has already been wrapped in {!s} for cmd {:s}."
            Logs.pprint('RED',msg.format('execute_build',type(bciuls_ctx),cmd_getting_wrapped))
         pass
      else:
         if debug_build_variants:
            msg = "Function {:s} being wrapped in {!s} for cmd {:s}."
            Logs.pprint(debug_bv_colour,msg.format(func_to_wrap.__name__,type(bciuls_ctx),cmd_getting_wrapped))
         #bciuls_ctx.execute = variant_decorator(func_to_wrap,variant_group_list)
         bciuls_ctx.execute_build = variant_decorator(platsys,func_to_wrap,variant_group_list)
   if debug_build_variants:
      Logs.pprint(debug_bv_colour,"########################### finished redirect_to_variants()")

def construct_variants(platsys,variant_group_list):
   # Construct all the variant machinery that can be done at the time of import (before the configuration step).
   # FIXME: see if this can be cached so it doesn't need to be done for every build as well as the config step....
   variant_name_path_list = construct_variant_names(variant_group_list)
   # Clone the build-like commands for each of the build variants.
   create_variant_commands(variant_name_path_list)
   # Now wrap the standard commands with a function that queues the appropriate clone(s) depending on the options.
   redirect_to_variants(platsys,variant_group_list)
   return variant_name_path_list

def variant_value(varname,variant_group_list):
   # Treat the first variant in each group as the most desirable of the group,
   # and the earlier groups as more desirable than later ones.
   val = 0
   for gx in range(len(variant_group_list)):
      val *=  2
      vfrag = variant_group_list[gx][0]
      if vfrag in varname:
         val += 1
   return val
