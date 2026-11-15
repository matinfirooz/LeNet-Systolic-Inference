`timescale 1ns/1ps
module pe_os(input wire clk,rst,clear,enable,
 input wire signed [15:0] a_in,b_in,input wire av_in,bv_in,
 output reg signed [15:0] a_out,b_out,output reg av_out,bv_out,
 output reg signed [47:0] accumulator);
 wire signed [31:0] product=a_in*b_in;
 always @(posedge clk) begin
  if(rst||clear) begin a_out<=0;b_out<=0;av_out<=0;bv_out<=0;accumulator<=0;end
  else if(enable) begin
   a_out<=a_in;b_out<=b_in;av_out<=av_in;bv_out<=bv_in;
   if(av_in&&bv_in) accumulator<=accumulator+{{16{product[31]}},product};
  end
 end
endmodule
