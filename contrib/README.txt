This directory contains contibutions that are not tested or maintained
as part of the TRE project but may still be useful.  (In some cases we
have no way at all to test these, so there is no guarantee they will
be up to date or work at all.)

   ps3 - a quick PS3 port of the TRE library, contributed by "bucanero"
         on 2021/03/25.

         Requirements:
            - open-source ps3 toolchain
            - open-source PSL1GHT SDK

         Build and install:
            - move up from the contrib directory to the main TRE directory
            - from the main TRE directory:
               make -f ps3/Makefile install
