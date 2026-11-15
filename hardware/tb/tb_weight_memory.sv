`timescale 1ns/1ps
module tb_weight_memory;
 parameter integer CACHE_ENABLE=1;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,req=0,ready=0;reg[15:0]address=0;wire req_ready,valid;wire[15:0]data;
 wire[31:0]requests,hits,reads;
 weight_memory #(.CACHE_ENABLE(CACHE_ENABLE))dut(clk,rst,req,req_ready,address,valid,ready,data,requests,hits,reads);
 reg[15:0]gold[0:61469];integer tick=0,seed=73,i,v,old_reads,old_hits,accepted;
 always @(posedge clk)tick=tick+1;
 task check_word(input integer a);
  reg[15:0]held;integer latency,hit_before;
  begin
   @(negedge clk);while(!req_ready)@(negedge clk);address=a;req=1;ready=0;hit_before=hits;
   @(posedge clk);#1;accepted=tick;
   @(negedge clk);req=0;
   while(!valid)@(negedge clk);
   latency=tick-accepted+1;held=data;
   if(data!==gold[a])$fatal(1,"weight address %0d expected %h got %h",a,gold[a],data);
   if(!CACHE_ENABLE&&latency!=4)$fatal(1,"L2 latency %0d",latency);
   if(CACHE_ENABLE&&hits>hit_before&&latency!=1)$fatal(1,"L1 hit latency %0d",latency);
   repeat(3)begin @(negedge clk);if(!valid||data!==held)$fatal(1,"memory response did not hold");end
   ready=1;@(negedge clk);ready=0;
  end
 endtask
 initial begin
  $readmemh("hardware/mem/weights.hex",gold);repeat(4)@(negedge clk);rst=0;
  check_word(0);if(CACHE_ENABLE&&reads!=8)$fatal(1,"cold line reads %0d",reads);
  old_reads=reads;old_hits=hits;check_word(1);
  if(CACHE_ENABLE&&(reads!=old_reads||hits!=old_hits+1))$fatal(1,"spatial hit failed");
  check_word(512);check_word(1);old_reads=reads;check_word(61469);
  if(CACHE_ENABLE&&reads-old_reads!=6)$fatal(1,"last line padding read out of range");
  for(i=0;i<120;i=i+1)begin v=$random(seed)&1023;check_word(v);end
  // Cancel an in-flight miss and verify a cold restart.
  @(negedge clk);address=2400;req=1;@(negedge clk);req=0;repeat(2)@(negedge clk);rst=1;
  repeat(3)@(negedge clk);rst=0;if(valid||!req_ready)$fatal(1,"memory reset failed");check_word(0);
  $display("PASS weight_memory cache=%0d reads=126 plus cancelled miss; L2=4 clocks; L1 hit=1 clock; response holds; conflict/tail/reset checked",CACHE_ENABLE);$finish;
 end
endmodule
