`timescale 1ns/1ps
module tanh_lut #(parameter INIT_FILE="hardware/mem/tanh.hex")(
 input wire clk,enable,input wire signed[47:0]accumulator,output reg signed[15:0]value);
 (* rom_style="block" *)reg signed[15:0]memory[0:4096];
 wire signed[48:0]rounded=($signed({accumulator[47],accumulator})+49'sd32768)>>>16;
 wire[12:0]address=(rounded< -49'sd2048)?13'd0:((rounded>49'sd2048)?13'd4096:rounded+49'sd2048);
 initial $readmemh(INIT_FILE,memory);
 always @(posedge clk)if(enable)value<=memory[address];
endmodule
