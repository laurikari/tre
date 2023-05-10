#                            # !/usr/bin/env python3
# encoding: utf-8
#
import tre

import sysconfig
import argparse
import sys

def get_bpc(s):
    maxordinal = ord(max(s, default='\0'))
    if maxordinal < 256:
        return 1
    elif maxordinal < 65536:
        return 2
    else:
        return 4

parser = argparse.ArgumentParser()
parser.add_argument("-o","--output",help="output file name")
args = parser.parse_args()
if args.output:
   ofs = open(args.output,mode="w",encoding="utf-8")
else:
   ofs = sys.stdout


fz0 = tre.Fuzzyness(maxerr = 0)
fz3 = tre.Fuzzyness(maxerr = 3)
env_path = sysconfig.get_path("platlib")
env_path = env_path[env_path.find("build"):]
env_path = env_path[0:env_path.find("/site-packages")]
if not args.output:
   # This output includes the platform/system, which we don't want to
   # allow for in the expected output, so we skip it if the output is
   # to a file.
   ofs.write("Running test in {:s}\n".format(env_path))
ofs.write("---- Fuzzyness with maxerr 0\n")
ofs.write("{!s}\n".format(fz0))
ofs.write("---- Fuzzyness with maxerr 3\n")
ofs.write("{!s}\n".format(fz3))
ofs.write("==== Start of tests\n")

# A list of tests, each being a tuple of:
#   (pattern,          str/bytes,
#    flags,            int,
#    match subject     str/bytes,
#    fuzzyness         tre.Fuzzyness,  # (Yeah, yeah, English has a quirk where the adverb fuzzy becomes the noun fuzziness, so what?)
#    expected results  (like tre.Match))
#       Note that these expected results are only expected if the codepoint sizes are suitable, the extension will generate
#       a ValueError exception when the build is for narrow characters only but any of the input values contain wide characters.
#
# A tre.Match object m is like a tuple of the matches to pattern applied to the subject,
# with:
#    m[0] being the match of the entire pattern, and
#    m[i] for i > 0 being either the match for the ith sub group in the pattern (if there is one) or None if the sub group did not match.
# It also has two methods:
#    m.groups() - returns a tuple of 'slice' indexes that would apply to the subject string
#    m.group(i) - for 0 <= i < len(m.groups()) returns the matching slice of the subject string if the ith sub group matched, otherwise None.
#                 (This method may produce exceptions if the subject string is modified after the match is generated.)
#
test_list = [
   ("Don(ald( Ervin)?)? Knuth",
    tre.EXTENDED,
    """
In addition to fundamental contributions in several branches of
theoretical computer science, Donnald Erwin Kuth is the creator of the
TeX computer typesetting system, the related METAFONT font definition
language and rendering system, and the Computer Modern family of
typefaces.

""",
    fz3,
    [(95, 113), (99, 108), (102, 108)]),
   ("xyzzy",
    tre.EXTENDED,
    "qqsvxyzzyaabbcc",
    fz0,
    [(4,9)]),
   ("xyzzy",
    tre.EXTENDED,
    "qqsvxyzzyaabbccđžš",
    fz0,
    [(4,9)]),
   ("xyzzy",
    tre.EXTENDED,
    "qqsvxyzzyaabbcc😀",
    fz0,
    [(4,9)])
]

fail_count = 0
pass_count = 0
for tst in test_list:
   pattern = tst[0]
   fuzzyness = tst[1]
   subject = tst[2]
   flags = tst[3]
   expected = tst[4]
   test_num = pass_count + fail_count
   ofs.write("+++ Test {:d} pattern: {!s}\n".format(test_num,pattern))
   ofs.write("... Subject: {!s}\n".format(subject))
   ofs.write("~~~ Codepoint size: p={:d} s={:d}\n".format(get_bpc(pattern),get_bpc(subject)))
   try:
      pt = tre.compile(pattern,fuzzyness)
   except ValueError as val_err:
      fail_count += 1
      ofs.write("XXX Test {:d} failed (ValueError in compile({!s}) --> {!s}\n".format(test_num,pattern,val_err))
      continue
   try:
      m = pt.search(subject,flags)
   except ValueError as val_err:
      fail_count += 1
      ofs.write("XXX Test {:d} failed (ValueError in search({!s}) --> {!s}\n".format(test_num,subject,val_err))
      continue
   if None == m:
      # The match didn't find anything.
      if None == tst[4]:
         # And it wasn't supposed to.
         pass_count += 1
         ofs.write("=== Test {:d} passed\n".format(test_num))
      else:
         ofs.write("XXX Test {:d} failed (did not match when it should have)\n".format(test_num))
         fail_count += 1
   else:
      # The match found something.
      if None == tst[4]:
         # And it wasn't supposed to.
         ofs.write("XXX Test {:d} failed (matched when it should not have)\n".format(test_num))
         fail_count += 1
      else:
         # Figure out if m has the values it should.
         groups = m.groups()
         ofs.write("    len(m.groups())={:d}\n".format(len(groups)))
         ofs.write("    m.groups: {!s}\n".format(groups))
         for slice in groups:
            ofs.write("      {!s} ---> {:s}\n".format(slice,subject[slice[0]:slice[1]]))
         for ndx in range(len(groups)):
            ofs.write("    m.[{:d}]: {!s}\n".format(ndx,m[ndx]))
         if len(expected) != len(groups):
            ofs.write("XXX Test {:d} failed (expected {:d} groups, got {:d}\n".format(test_num,len(expected),len(groups)))
            fail_count += 1
         else:
            # We have the right number of sub groups, check each one.
            failed = False
            for ndx in range(len(groups)):
               expected_slice = expected[ndx]
               matched_slice = groups[ndx]
               if None == expected_slice and None != matched_slice:
                  ofs.write("XXX Test {:d} failed: subgroup {:d} matched when it should not have\n".format(test_num,ndx))
                  failed = True
               elif None != expected_slice and None == matched_slice:
                  ofs.write("XXX Test {:d} failed: subgroup {:d} did not match when it should have\n".format(test_num,ndx))
                  failed = True
               elif None != expected_slice and None != matched_slice:
                  # Check the actual values.
                  if expected_slice[0] != matched_slice[0] or expected_slice[1] != matched_slice[1]:
                     msg = "XXX Test {:d} failed: subgroup {:d} did not match as it should have, expected {!s}, got {!s}\n"
                     ofs.write(msg.format(test_num,ndx,expected_slice,matched_slice))
                     failed = True
               # else: # Both == None is a pass
            if failed:
               fail_count += 1
            else:
               pass_count += 1
               ofs.write("=== Test {:d} passed\n".format(test_num))

if 0 == fail_count:
   ofs.write("#### All {:d} tests passed.\n".format(pass_count))
elif 0 == pass_count:
   ofs.write("#### {:d} tests failed miserably.\n".format(fail_count))
else:
   ofs.write("#### {:d} passed, {:d} failed.\n".format(pass_count,fail_count))
