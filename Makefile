all: build

########################################
# check that all the submodules are here
########################################

mahimahi/src/frontend/delayshell.cc ccp-kernel/libccp/ccp.h bbr/src/lib.rs empirical-traffic-gen/src/client.c:
	$(error Did you forget to git submodule update --init --recursive ?)

#########################
# compile all the things!
#########################

ccp-kernel/ccp.ko:
	$(MAKE) -C ccp-kernel

mahimahi/configure:
	cd mahimahi && autoreconf -i

mahimahi/Makefile: mahimahi/configure
	cd mahimahi && ./configure

mahimahi/src/frontend/mm-delay: mahimahi/src/frontend/delayshell.cc mahimahi/Makefile
	$(MAKE) -C mahimahi

mahimahi: mahimahi/src/frontend/mm-delay

portus/ccp_generic_cong_avoid/target/debug/reno portus/ccp_generic_cong_avoid/target/debug/cubic:
	$(MAKE) -C portus

#bbr/target/debug/bbr:
#	cd bbr && cargo +nightly build
#
#bbr: bbr/target/debug/bbr
cubic: portus/ccp_generic_cong_avoid/target/debug/cubic
reno: portus/ccp_generic_cong_avoid/target/debug/reno 

empirical-traffic-gen/bin/server empirical-traffic-gen/bin/client:
	$(MAKE) -C empirical-traffic-gen

build: ccp-kernel/ccp.ko mahimahi/src/frontend/mm-delay portus/ccp_generic_cong_avoid/target/debug/reno

##################
# run experiments 
##################

results:
	mkdir -p results
