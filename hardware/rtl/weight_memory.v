`timescale 1ns/1ps
module weight_memory #(parameter integer CACHE_ENABLE=0,parameter INIT_FILE="hardware/mem/weights.hex")(
 input wire clk,rst,req_valid,output wire req_ready,input wire[15:0]req_address,
 output wire resp_valid,input wire resp_ready,output wire[15:0]resp_data,
 output wire[31:0]request_count,hit_count,l2_reads);
 wire dv,dr,rv,rr;wire[15:0]da,rd;
 dram_model #(.LATENCY(4),.INIT_FILE(INIT_FILE))u_dram(clk,rst,dv,dr,da,rv,rr,rd,l2_reads);
 generate if(CACHE_ENABLE)begin:CACHED
  weight_cache u_cache(clk,rst,req_valid,req_ready,req_address,resp_valid,resp_ready,resp_data,
   dv,dr,da,rv,rr,rd,request_count,hit_count);
 end else begin:DIRECT
  assign dv=req_valid;assign req_ready=dr;assign da=req_address;assign resp_valid=rv;
  assign rr=resp_ready;assign resp_data=rd;assign request_count=l2_reads;assign hit_count=32'd0;
 end endgenerate
endmodule
