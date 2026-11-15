`timescale 1ns/1ps
// A request accepted at edge e can retire at edge e+LATENCY. One outstanding word.
module dram_model #(parameter integer DEPTH=61470,LATENCY=4,parameter INIT_FILE="hardware/mem/weights.hex")(
 input wire clk,rst,req_valid,output wire req_ready,input wire[15:0]req_address,
 output wire resp_valid,input wire resp_ready,output reg[15:0]resp_data,output reg[31:0]read_count);
 (* rom_style="block" *) reg[15:0]memory[0:DEPTH-1];
 reg busy;reg[3:0]remaining;
 initial $readmemh(INIT_FILE,memory);
 assign resp_valid=busy&&(remaining==0);
 assign req_ready=!busy||(resp_valid&&resp_ready);
 always @(posedge clk) begin
  if(rst)begin busy<=0;remaining<=0;resp_data<=0;read_count<=0;end
  else begin
   if(busy&&remaining!=0)remaining<=remaining-1'b1;
   if(resp_valid&&resp_ready)busy<=0;
   if(req_valid&&req_ready)begin
    busy<=1;remaining<=LATENCY-1;read_count<=read_count+1'b1;
    resp_data<=(req_address<DEPTH)?memory[req_address]:16'd0;
   end
  end
 end
endmodule
