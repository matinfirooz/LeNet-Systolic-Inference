set root [file normalize [file join [file dirname [info script]] ../..]]
set mode ws
set cache 0
set stage post_route
if {[llength $argv]>0} {set mode [lindex $argv 0]}
if {[llength $argv]>1} {set cache [lindex $argv 1]}
if {[llength $argv]>2} {set stage [lindex $argv 2]}
open_checkpoint [file join $root results vivado ${mode}_cache${cache} ${stage}.dcp]
start_gui
# In the GUI select an instance, open Schematic and export that actual Vivado view.
