# Matin Firoozbakht | @matinfirooz. Run from any directory with Vivado installed.
set root [file normalize [file join [file dirname [info script]] ../..]]
cd $root
set mode ws
if {[info exists ::env(LENET_DATAFLOW)]} {set mode $::env(LENET_DATAFLOW)}
if {$mode ni {ws os is}} {error "LENET_DATAFLOW must be ws, os or is"}
set cache 0
if {[info exists ::env(LENET_CACHE)]} {set cache $::env(LENET_CACHE)}
if {$cache ni {0 1}} {error "LENET_CACHE must be 0 or 1"}
set part xc7a100tcsg324-1
if {[info exists ::env(FPGA_PART)]} {set part $::env(FPGA_PART)}
set period 10.0
if {[info exists ::env(CLOCK_PERIOD_NS)]} {set period $::env(CLOCK_PERIOD_NS)}
set top lenet_top_$mode
set out [file join $root results vivado ${mode}_cache${cache}]
file mkdir $out
set files [split [string trim [read [set fh [open hardware/rtl/files.f r]]]] "\n"]
close $fh
read_verilog -sv $files
synth_design -top $top -part $part -mode out_of_context -generic CACHE_ENABLE=$cache
create_clock -name core_clk -period $period [get_ports clk]
set inputs [get_ports -filter {DIRECTION == IN && NAME != clk}]
set outputs [get_ports -filter {DIRECTION == OUT}]
set_input_delay -clock core_clk -max [expr {$period*0.2}] $inputs
set_input_delay -clock core_clk -min [expr {$period*0.02}] $inputs
set_output_delay -clock core_clk -max [expr {$period*0.2}] $outputs
set_output_delay -clock core_clk -min [expr {$period*0.02}] $outputs
write_checkpoint -force [file join $out post_synth.dcp]
report_utilization -hierarchical -file [file join $out utilization_synth.rpt]
opt_design
place_design
phys_opt_design
route_design
write_checkpoint -force [file join $out post_route.dcp]
report_utilization -hierarchical -file [file join $out utilization_route.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -max_paths 10 -warn_on_violation -file [file join $out timing_route.rpt]
report_drc -file [file join $out drc.rpt]
check_timing -verbose -file [file join $out check_timing.rpt]
set activity vectorless
if {[info exists ::env(LENET_SAIF)]} {
 if {[info exists ::env(LENET_SAIF_SCOPE)]} {
  read_saif -strip_path $::env(LENET_SAIF_SCOPE) -out_file [file join $out saif_annotation.rpt] $::env(LENET_SAIF)
 } else {read_saif -out_file [file join $out saif_annotation.rpt] $::env(LENET_SAIF)}
 set activity saif_annotated
}
report_power -file [file join $out power_route.rpt]
set setup_paths [get_timing_paths -delay_type max -max_paths 1]
set hold_paths [get_timing_paths -delay_type min -max_paths 1]
set wns null
set whs null
if {[llength $setup_paths]} {set wns [get_property SLACK $setup_paths]}
if {[llength $hold_paths]} {set whs [get_property SLACK $hold_paths]}
set fh [open [file join $out implementation.json] w]
puts $fh [format {{"top":"%s","part":"%s","cache_enable":%d,"clock_period_ns":%s,"setup_wns_ns":%s,"hold_whs_ns":%s,"activity":"%s","implementation_mode":"out_of_context"}} $top $part $cache $period $wns $whs $activity]
close $fh
puts "Routed core saved in $out. Inspect timing, unconstrained paths, DRC and SAIF coverage before qualifying a throughput/power result."
