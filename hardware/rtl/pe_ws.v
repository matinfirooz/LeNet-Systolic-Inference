`timescale 1ns/1ps
module pe_ws(input wire clk,rst,load,enable,input wire signed [15:0] weight_in,a_in,
 input wire av_in,sv_in,input wire signed [47:0] sum_in,
 output reg signed [15:0] a_out,output reg av_out,sv_out,
 output reg signed [47:0] sum_out);
 reg signed [15:0] weight;
 wire signed [31:0] product=a_in*weight;
 always @(posedge clk) begin
  if(rst) begin weight<=0;a_out<=0;av_out<=0;sv_out<=0;sum_out<=0;end
  else if(load) begin weight<=weight_in;a_out<=0;av_out<=0;sv_out<=0;sum_out<=0;end
  else if(enable) begin
   a_out<=a_in;av_out<=av_in;sv_out<=av_in&&sv_in;
   if(av_in&&sv_in) sum_out<=sum_in+{{16{product[31]}},product};
  end
 end
endmodule
