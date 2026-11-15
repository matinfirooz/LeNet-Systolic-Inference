`timescale 1ns/1ps
module activation_memory(input wire clk,read_enable,read_bank,input wire[12:0]read_address,
 output reg signed[15:0]read_data,input wire write_enable,write_bank,input wire[12:0]write_address,
 input wire signed[15:0]write_data);
 (* ram_style="block" *)reg signed[15:0]bank0[0:8191],bank1[0:8191];
 always @(posedge clk)begin
  if(read_enable)read_data<=read_bank?bank1[read_address]:bank0[read_address];
  if(write_enable)begin if(write_bank)bank1[write_address]<=write_data;else bank0[write_address]<=write_data;end
 end
endmodule
