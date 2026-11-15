`timescale 1ns/1ps
module pe_is(input wire clk,rst,load,enable,input wire signed [15:0] activation_in,b_in,
 input wire bv_in,sv_in,input wire signed [47:0] sum_in,
 output reg signed [15:0] b_out,output reg bv_out,sv_out,
 output reg signed [47:0] sum_out);
 reg signed [15:0] activation;
 wire signed [31:0] product=activation*b_in;
 always @(posedge clk) begin
  if(rst) begin activation<=0;b_out<=0;bv_out<=0;sv_out<=0;sum_out<=0;end
  else if(load) begin activation<=activation_in;b_out<=0;bv_out<=0;sv_out<=0;sum_out<=0;end
  else if(enable) begin
   b_out<=b_in;bv_out<=bv_in;sv_out<=bv_in&&sv_in;
   if(bv_in&&sv_in) sum_out<=sum_in+{{16{product[31]}},product};
  end
 end
endmodule
