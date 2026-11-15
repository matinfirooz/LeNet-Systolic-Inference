`timescale 1ns/1ps
module bias_rom #(parameter INIT_FILE="hardware/mem/biases.hex")(
 input wire clk,read_enable,input wire[7:0]address,output reg signed[47:0]data);
 (* rom_style="block" *)reg signed[47:0]memory[0:235];
 initial $readmemh(INIT_FILE,memory);
 always @(posedge clk)if(read_enable)data<=memory[address];
endmodule
